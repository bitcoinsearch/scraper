import copy
import datetime
import hashlib
import json
import os
import re
import string
import sys
import traceback
from collections import defaultdict, abc

import tldextract

from scraper_generator_custom_node import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapegraphai.nodes import ParseNode, FetchNode, GenerateAnswerNode
from scrapegraphai.graphs import ScriptCreatorGraph
from common.elasticsearch_utils import upsert_document

from bs4 import BeautifulSoup
from elasticsearch import Elasticsearch
from scraper_prompts import base_prompt, get_tags_prompt
from custom_graph import CustomScraperGraph
import dateutil

from dotenv import load_dotenv

load_dotenv()

INDEX = os.getenv("INDEX")
DATA_DIR = os.getenv('DATA_DIR')

es = Elasticsearch(
    cloud_id=os.getenv("CLOUD_ID"),
    api_key=os.getenv("USER_PASSWORD")
)


def build_scrapegraph_prompt(extraction_config):
    prompt = base_prompt.format(", ".join(extraction_config["datapoints"]))
    return str(prompt)


def get_script_from_llm(chunks, prompt, state, model_config, url):
    prompt = copy.deepcopy(prompt)
    filename = hashlib.md5(bytes(str(datetime.datetime.now()),
                                 encoding="utf8")).hexdigest()[:5] + ".json"
    prompt += f"\nMake the main function named `main` which takes `url` (source) and `filename` (used to dump output as json) as parameters."
    prompt += "\nThese are builtin environment parameters."
    prompt += "\nAdd null checks and index checks wherever necessary like when methods are daisy chained. Verify a key exists in dictionary and verify if the output of a method os not None before operationg on it."
    prompt += "\nOnly use HTML/CSS/JS information, keep the code generalized for similar pages with different content."
    prompt += "\n\nAdd the following driver code at the end which will supply the necessary inputs:\n"
    prompt += "main(url=globals().get('url'), filename=globals().get('filename'))"

    graph = CustomScraperGraph(prompt=prompt, config=model_config, source=url)
    generate_scraper_node = GenerateScraperNode(
        input="user_prompt & (relevant_chunks | parsed_doc | doc | chunks)",
        output=["answer"],
        node_config={
            "llm_model": graph.llm_model,
            "additional_info": graph.config.get("additional_info"),
            "schema": graph.schema,
        },
        library=graph.library,
        website=graph.source
    )
    site_name = tldextract.extract(url)
    site_name = site_name.subdomain + '.' + site_name.domain + '.' + site_name.suffix
    site_name = site_name.strip('.')
    if not os.path.exists("generated_scripts/" + site_name + ".py"):
        # Execute the generate answer node
        for _ in range(3):
            try:
                # Define the state
                state = {"user_prompt": str(prompt), "chunks": chunks}
                json.dump(chunks, open("chunks.json", "w"), indent=4)
                state = generate_scraper_node.execute(state)
                # Retrieve the generated answer from the state
                result = state["answer"]
                result = "\n".join(result.split("\n")[1:-1])
                result = re.sub(r'[\"\']output.json[\"\']', "filename", result)
                result = re.sub(r'\"?\'?' + url + r'\"?\'?', "url", result)
                result_json = exec(result, {'filename': filename, "url": url})
            except Exception as e:
                print("RETYING ::", e, flush=True)
                prompt += "\nThis code generates error.\n" + result + "\nWrite code such that this is avoided " + traceback.format_exc()
                continue
    else:
        with open("generated_scripts/" + site_name + ".py") as f:
            result = f.read()
            result_json = exec(result, {'filename': filename, "url": url})
    try:
        result_json = json.load(open(filename))
        os.remove(filename)
        os.makedirs("generated_scripts", exist_ok=True)
        with open("generated_scripts/" + site_name + ".py", "w") as f:
            f.write(result)
        print("filename = ", filename)
    except Exception as e:
        traceback.print_exc()
        result_json = {}
    return result, result_json


def call_scrapegraph_script_generator(prompt, url, model_config):
    print("PROCESSING >>>>>>>>>>>>>>>> ", url, flush=True)
    prompt = copy.deepcopy(prompt)
    filename = hashlib.md5(bytes(str(datetime.datetime.now()),
                                 encoding="utf8")).hexdigest()[:5] + ".json"
    prompt += f"\nMake the main function named `main` which takes `url` (source) and `filename` (used to dump output as json) as parameters."
    prompt += "\nThese are builtin environment parameters."
    prompt += "\nAdd null checks and index checks wherever necessary like when methods are daisy chained. Verify a key exists in dictionary and verify if the output of a method os not None before operationg on it."
    prompt += "\nOnly use HTML/CSS/JS information, keep the code generalized for similar pages with different content."
    prompt += "\n\nAdd the following driver code at the end which will supply the necessary inputs:\n"
    prompt += "main(url=globals().get('url'), filename=globals().get('filename'))"

    site_name = tldextract.extract(url)
    site_name = site_name.subdomain + '.' + site_name.domain + '.' + site_name.suffix
    site_name = site_name.strip('.')
    if not os.path.exists("generated_scripts/" + site_name + ".py"):
        # Create the script creator graph
        for _ in range(3):
            try:
                script_creator = ScriptCreatorGraph(prompt, url, model_config)
                # Run the script creator graph
                result = script_creator.run()
                result = "\n".join(result.split("\n")[1:-1])
                result = re.sub(r'[\"\']output.json[\"\']', "filename", result)
                result = re.sub(r'\"?\'?' + url + r'\"?\'?', "url", result)
                result_json = exec(result, {'filename': filename, "url": url})
            except Exception as e:
                print("RETYING ::", e, flush=True)
                prompt += "\nThis code generates error.\n" + result + "\nWrite code such that this is avoided " + traceback.format_exc()
                continue
    else:
        with open("generated_scripts/" + site_name + ".py") as f:
            result = f.read()
            result_json = exec(result, {'filename': filename, "url": url})
    try:
        result_json = json.load(open(filename))
        os.remove(filename)
        os.makedirs("generated_scripts", exist_ok=True)
        with open("generated_scripts/" + site_name + ".py", "w") as f:
            f.write(result)
        print("filename = ", filename)
    except Exception as e:
        traceback.print_exc()
        result_json = {}
    return result, result_json


def sanitize_html_for_json(body_html):
    body_html = body_html.replace(r"\e", r"\\e")
    return body_html


def fetch_data(url, extraction_config, model_config):
    fetch_node = FetchNode(
        input="url",
        output=["fetched_content", "link_urls", "image_urls"],
        node_config={
            "llm_model": model_config["llm"],
            "force": False,  # extraction_config.get("markdown", False),  # Convert to Markdown
            "cut": extraction_config.get("clean_html", True),  # Cleanup html
            # "loader_kwargs": {},
        }
    )
    # Define the state
    state = {"url": url}
    # Execute the fetch node
    state = fetch_node.execute(state)
    # Retrieve the fetched content and other information from the state
    fetched_content = state["fetched_content"]
    body = None
    # Currently scrapegraph does not return image_urls and link_urls
    link_urls = state.get("link_urls", [])
    image_urls = state.get("image_urls", [])

    # if fetched_content and not extraction_config.get("markdown", False):
    body_html = fetched_content[0].page_content
    print("BODY HTML = ", type(body_html))
    soup = BeautifulSoup(body_html)
    body = soup.get_text("\n")
    # Extract image urls manually
    image_urls = []
    html = soup.findAll('img')
    for im in html:
        if im.get("src", None) is None:
            continue
        if im['src'].startswith("/"):  # allow any protocol
            im['src'] = os.path.join(url, im['src'].strip('/'))
        image_urls.append(im['src'])
    # Extract links manually
    html = soup.findAll('a')
    for link in html:
        if link.has_attr('href'):
            if link['href'].startswith("/"):  # allow any protocol
                link["href"] = os.path.join(url, link['href'].strip('/'))
            link_urls.append(link["href"])
    for tag in soup():
        for attribute in ["name", "style", "path", "srcset"]:
            del tag[attribute]
    _ = [tag.decompose() for tag in soup("script")]
    _ = [tag.decompose() for tag in soup("style")]
    _ = [tag.decompose() for tag in soup("path")]
    _ = [tag.clear() for tag in soup("script")]
    _ = [tag.clear() for tag in soup("style")]
    _ = [tag.clear() for tag in soup("path")]
    body_html = str(soup)
    body_html = sanitize_html_for_json(body_html)
    state["fetched_content"][0].page_content = body_html
    if not fetched_content:
        fetched_content = [None]

    results = {
        "body_formatted": body,
        "body": body_html,  # getattr(fetched_content[0], "page_content", None),
        "link_urls": link_urls,
        "image_urls": image_urls
    }
    return soup, state, results


def parse_data_for_llm(state):
    parse_node = ParseNode(
        input="fetched_content",
        output=["chunks"],
        node_config={"verbose": True, "parse_html": False},  # "chunk_size": 8192,}
        node_name="Parse"
    )
    state = parse_node.execute(state)
    # Retrieve the parsed content chunks from the state
    chunks = state["chunks"]
    return chunks


def get_answers_from_llm(chunks, prompt, state, model_config):
    graph = CustomScraperGraph(prompt=prompt, config=model_config)
    # Define the state
    state = {"user_prompt": str(prompt), "chunks": chunks}

    generate_answer_node = GenerateAnswerNode(
        input="user_prompt & (relevant_chunks | parsed_doc | doc | chunks)",
        output=["answer"],
        node_config={
            "llm_model": graph.llm_model,
            "additional_info": graph.config.get("additional_info"),
            "schema": graph.schema,
        }
    )

    # Execute the generate answer node
    state = generate_answer_node.execute(state)
    # state = graph.run(state)
    # Retrieve the generated answer from the state
    answer = state["answer"]
    # print(f"Generated Answer: {answer}")
    return answer


def get_title(soup):
    title = soup.find('title')
    return title


def get_all_classes(soup):
    tag_class_list = []
    # get all tags
    tags = {tag.name for tag in soup.find_all()}
    # iterate all tags
    for tag in tags:
        # find all element of tag
        for i in soup.find_all(tag):
            # if tag has attribute of class
            if i.has_attr("class"):
                if len(i['class']) != 0:
                    tag_class_list.append(tag + ": " + " ".join(i['class']))
    return tag_class_list


def make_ollama_call(model_name, message_text):
    import ollama
    response = ollama.chat(model=model_name,
                           messages=[
                               {
                                   'role': 'user',
                                   'content': message_text,
                               },
                           ])
    # print(response['message']['content'])
    return response['message']['content']


def get_probable_tags(all_tag_classes, keys_to_extract):
    if "ollama" in model_config["llm"]["model"]:
        probable_tags = make_ollama_call(
            model_config["llm"]["model"].split('/')[-1],
            get_tags_prompt.format(" ".join(keys_to_extract), "\n".join(all_tag_classes))
        )
        probable_tags = probable_tags.split("\n")
        probable_tags = [i.strip().strip('`').strip() for i in probable_tags]
        # print("PROBABLE TAGS =", probable_tags)
        probable_tags = [i for i in probable_tags if ':' in i and i.split(':')[-1] in all_tag_classes]
        key_tag_mapping = {i: [j.split(':')[-1] for j in probable_tags] for i in keys_to_extract}
        return key_tag_mapping
    return {}


def get_text_from_tags(soup, key_tag_mapping):
    key_values = {i: [] for i in key_tag_mapping}
    for key, tags in key_tag_mapping.items():
        for tag in tags:
            result = soup.find_all(
                tag.split(':')[0].strip(), {"class": tag.split(':')[-1].strip()})
            key_values[key].append(result.text)
    return key_values


def postprocess_llm_results(llm_results, html_body):
    """
    recursively traverse lists and dictionaries,
    if a string value is found, verify it exists in the html source
    """
    if isinstance(llm_results, dict):
        processed_dict = {}
        for k, v in llm_results.items():
            if v is None:
                processed_dict[k] = v
            if isinstance(v, str):
                if v in ["NA", "na", "None", "null"]:
                    # processed_dict[k] = v
                    continue
                elif v in html_body:
                    processed_dict[k] = v
            if isinstance(v, (list, dict)):
                processed_dict[k] = postprocess_llm_results(v, html_body)

        return processed_dict
    if isinstance(llm_results, list):
        processed_list = []
        for v in llm_results:
            if v is None:
                processed_list.append(v)
            if isinstance(v, (list, dict)):
                processed_list.append(postprocess_llm_results(v, html_body))
            elif isinstance(v, str):
                if v in html_body:
                    processed_list.append(v)
        return processed_list
    return llm_results


def flatten_llm_results(llm_results, output_dict=None):
    if output_dict is None:
        output_dict = {}
    # if isinstance(llm_results, dict):
    #     print(llm_results.keys())
    # else:
    #     print(llm_results)
    if isinstance(llm_results, dict):
        for k, v in llm_results.items():
            if isinstance(v, str):
                if k not in output_dict:
                    output_dict[k] = v
                elif type(output_dict[k]) == type(v):
                    if k in ["author", "writer", "published by", "time", "published date", "created_at"]:
                        # Replace only if previous value invalid as these are either at the top or bottom of the page
                        if len(output_dict[k].strip(string.punctuation +
                                                    " ")) == 0 or output_dict[k] in [
                            "NA", "na", "None", "null"
                        ]:
                            output_dict[k] = v
                        elif len(v.strip(string.punctuation +
                                         " ")) >= 0 and v not in [
                            "NA", "na", "None", "null"
                        ]:
                            # Add as key_<count>
                            k_similar = [i for i in output_dict.keys() if i.startswith(k)]
                            output_dict[f"{k}_{len(k_similar) + 1}"] = v
                    else:
                        # for other keys, keep the one with max length
                        output_dict[k] = v if len(v) > len(output_dict[k]) else output_dict[k]

            elif isinstance(v, list):
                if all(isinstance(i, str) for i in v):
                    if k not in output_dict:
                        output_dict[k] = v
                    elif isinstance(output_dict[k], list):
                        output_dict[k].extend(v)
                    else:
                        k_similar = [i for i in output_dict.keys() if i.startswith(k)]
                        output_dict[f"{k}_{len(k_similar) + 1}"] = v
                else:
                    k_strs, flat_list, flat_dict = flatten_llm_results(v, output_dict)
                    if len(k_strs) > 0:
                        if k not in output_dict:
                            output_dict[k] = k_strs
                        elif isinstance(output_dict[k], list) and isinstance(output_dict[k][0], str):
                            output_dict[k].extend(k_strs)
                        else:
                            k_similar = [i for i in output_dict.keys() if i.startswith(k)]
                            output_dict[f"{k}_{len(k_similar) + 1}"] = k_strs
                    if len(flat_list) > 0:
                        if k not in output_dict:
                            output_dict[k] = flat_list
                        else:
                            k_similar = [i for i in output_dict.keys() if i.startswith(k)]
                            output_dict[f"{k}_{len(k_similar) + 1}"] = flat_list
                    if len(flat_dict) > 0:
                        for k_, v_ in flat_dict.items():
                            if k_ not in output_dict:
                                output_dict[k_] = v_
                            elif f"{k_}_{k}" not in output_dict:
                                output_dict[f"{k_}_{k}"] = v_
                            else:
                                k_similar = [i for i in output_dict.keys() if i.startswith(f"{k_}_{k}")]
                                output_dict[f"{k_}_{k}_{len(k_similar) + 1}"] = v_
            elif isinstance(v, dict):
                flatten_llm_results(v, output_dict)

    if isinstance(llm_results, list):
        # Not processing nested lists as mapping to a global key will get complicated.
        # Extreme nesting is also unexpected.
        # Can be done by recursively calling with inidividual outputs
        if all([isinstance(i, str) for i in llm_results]):
            return llm_results
        k_strs = [i for i in llm_results if isinstance(i, str) if len(i) > 0]
        k_dicts = [flatten_llm_results(i, {}) for i in llm_results if isinstance(i, dict) if len(i) > 0]
        k_lists = [flatten_llm_results(i, {}) for i in llm_results if isinstance(i, list) if len(i) > 0]

        flat_dict = defaultdict(list)
        for i in k_dicts:
            for k, v in i.items():
                flat_dict[k].append(v)
        for k, v in flat_dict.items():
            if k in ["author", "writer", "published by", "time", "published date", "created_at"]:
                v = [
                    i for i in v
                    if (not isinstance(i, str)) or len(i.strip(string.punctuation +
                                                               " ")) >= 0  # and v not in ["NA", "na", "None", "null"]
                ]
                try:
                    if len(set(v)) > 0:
                        flat_dict[k] = list(set(v))
                except:
                    raise
            else:
                flat_dict[k] = v
        flat_dict = {k: v for k, v in flat_dict.items() if len(v) > 0}
        flat_list = [j for i in k_lists for j in i]
        return k_strs, flat_list, flat_dict
    return output_dict


def sanitize_nested_values(response_document):
    if isinstance(response_document, dict):
        for k, v in response_document.items():
            # For a dictionary, sanity check all the values inside through sanitize_values function
            if isinstance(v, dict):
                response_document[k] = v = sanitize_values(v)
            # Check values inside the updated v and recursively sanitize internal components
            if not isinstance(v, str):
                response_document[k] = sanitize_nested_values(v)

    elif isinstance(response_document, list):
        response_document = [sanitize_nested_values(v) for v in response_document]
    return response_document


def sanitize_values(response_document: dict):
    if not isinstance(response_document, dict):
        return response_document
    # Add llm_results as a key as if called from sanitize_nested_values,
    # it will not have the key
    added_llm_res = False  # Flag to remove the key later if added artificially
    if "llm_results" not in response_document:
        response_document["llm_results"] = {}
        added_llm_res = True

    if "created_at" in response_document:
        try:
            response_document["created_at"] = datetime.datetime.strftime(
                dateutil.parser.parse(response_document["created_at"]),
                "%Y-%m-%d")
        except:
            _ = response_document.pop("created_at")
    possible_keys = [
        i for i in response_document.keys() if "date" in i or "time" in i or "created_at" in i
    ]
    if "created_at" not in response_document:
        for i in possible_keys:
            if response_document[i] not in [
                "", "NA", None, "None", "null", "na"
            ]:
                try:
                    response_document[
                        "created_at"] = datetime.datetime.strftime(
                        dateutil.parser.parse(response_document[i]),
                        "%Y-%m-%d")
                    if "created_at" in response_document["llm_results"]:
                        response_document["llm_results"][
                            "created_at"] = response_document["created_at"]
                    break
                except:
                    continue
    for i in possible_keys:
        if response_document[i] not in ["", "NA", None, "None", "null", "na"]:
            try:
                response_document[i] = datetime.datetime.strftime(
                    dateutil.parser.parse(response_document[i]), "%Y-%m-%d")
                if i in response_document["llm_results"]:
                    response_document["llm_results"][i] = response_document[i]
            except:
                continue
        else:
            response_document[i] = None

    text_only_fields = ["author", "title"]
    for i in text_only_fields:
        if i in response_document and not isinstance(response_document[i], str):
            if isinstance(response_document[i], list):
                response_document[i + "_list"] = response_document["llm_results"][
                    i + "_list"] = response_document[i]
                if len(response_document[i]) > 0:
                    response_document[i] = response_document[i][0]
                    if i in response_document["llm_results"]:
                        response_document["llm_results"][i] = response_document[
                            "llm_results"][i][0]
                else:
                    response_document[i] = "NA"
                    response_document["llm_results"][i] = "NA"
            if isinstance(response_document[i], dict):
                response_document[i + "_dict"] = response_document["llm_results"][
                    i + "_dict"] = response_document[i]
                if "name" in response_document[i]:
                    response_document[i] = response_document["llm_results"][
                        i] = response_document[i]["name"]
                else:
                    for k, v in response_document[i].items():
                        if "name" in k:
                            response_document[i] = response_document[
                                "llm_results"][i] = response_document[i][k]
                    else:
                        response_document[i] = "NA"
                        response_document["llm_results"][i] = "NA"

    if added_llm_res:
        _ = response_document.pop("llm_results")

    return response_document


def main(url, extraction_config, model_config):
    # created_at, title, body, url, indexed_at, authors, id
    # Create base graph to get some llm parameters
    print(url)
    prompt = build_scrapegraph_prompt(extraction_config)

    response_document = {
        "url": url,
        "indexed_at": datetime.datetime.utcnow().isoformat()
        # "created_at": datetime.datetime.now(),
    }
    soup, state, results = fetch_data(url, extraction_config, model_config)

    title = get_title(soup)
    response_document.update(results)
    if title is not None and title.has_attr("text"):
        response_document["title_html"] = str(title.text)
    parsed_chunks = parse_data_for_llm(state)
    print(len(parsed_chunks))

    # if len(parsed_chunks) == 1:
    try:
        # Fails if text too long for model
        script_res_script, script_res_json = call_scrapegraph_script_generator(prompt, url, model_config)
    except:
        # Might not be as accurate as it generates multiple scripts and then merges them
        script_res_script, script_res_json = get_script_from_llm(parsed_chunks, prompt, state, model_config, url)
    if isinstance(script_res_json, dict):
        script_res_json = {
            k: v
            for k, v in script_res_json.items()
            if v not in ["", "NA", "na", "None", "null"]
        }
    for k, v in script_res_json.items():
        if v is not None and v not in ["", "NA", "na", "None", "null"]:
            prompt = prompt.replace(k + ", ", "")
    # except:
    #     with open("temp_script.py", "w") as f:
    #         f.write(script_res_temp)

    llm_results = get_answers_from_llm(parsed_chunks, prompt, state, model_config)
    # llm_results = response_document["llm_results"] = json.load(open("llm_results.json"))

    # Reload as json as some elements are tuples instead of lists
    llm_results = json.loads(json.dumps(llm_results))

    if isinstance(llm_results, list):
        llm_results = [i for i in llm_results if len(i) > 0]
    elif isinstance(llm_results, dict):
        llm_results = {
            k: v
            for k, v in llm_results.items()
            if (not isinstance(v, abc.Sized)) or (v is not None and len(v) > 0)
        }

    response_document["llm_results"] = postprocess_llm_results(
        llm_results, response_document["body"])

    response_document["llm_results"] = flatten_llm_results(
        response_document["llm_results"])

    # Add results from script based generator
    if isinstance(response_document["llm_results"], list):
        response_document["llm_results"].append(script_res_json)
    else:
        response_document["llm_results"].update(script_res_json)

    if isinstance(response_document["llm_results"], (list, tuple)) and len(
            response_document["llm_results"]) > 0 and isinstance(
        response_document["llm_results"][0], dict):
        response_document["llm_results"] = response_document["llm_results"][0]

    for main_key in ["author", "title", "created_at"]:
        if main_key in response_document["llm_results"] and isinstance(response_document["llm_results"], dict):
            if isinstance(response_document["llm_results"][main_key], list):
                response_document[main_key] = sorted(
                    response_document["llm_results"][main_key], key=lambda x: len(x))[-1]
            elif isinstance(response_document["llm_results"][main_key], str):
                response_document[main_key] = response_document["llm_results"][main_key]
            else:
                if main_key == "title":
                    response_document[main_key] = response_document.get("title_html", "NA")
    # print(response_document["title"])

    if response_document.get("created_at", None) is None:
        if "published/created date" in response_document["llm_results"]:
            if isinstance(response_document["llm_results"]["published/created date"], (list, tuple)):
                response_document["created_at"] = sorted(
                    response_document["llm_results"]["published/created date"],
                    key=lambda x: len(x))[-1]
            elif isinstance(response_document["llm_results"]["published/created date"], str):
                response_document["created_at"] = response_document["llm_results"]["published/created date"]

    # response_document["llm_results"] = [i for i in response_document["llm_results"] if len(i)>0]

    if len(response_document["llm_results"]) > 0 and isinstance(response_document["llm_results"], dict):
        try:
            for k, v in response_document["llm_results"].items():
                if k not in response_document:
                    response_document[k] = v
        except Exception as e:
            traceback.print_exc()
            print(response_document["url"], response_document["llm_results"])

    # Reload as json as some elements are tuples instead of lists
    response_document = json.loads(json.dumps(response_document))
    if isinstance(response_document["llm_results"], list):
        response_document["llm_results"] = [
            i for i in response_document["llm_results"] if i is not None and len(i) > 0
        ]
    elif isinstance(response_document["llm_results"], dict):
        response_document["llm_results"] = {
            k: v
            for k, v in response_document["llm_results"].items()
            if v is not None and v not in ["", "NA", "na", "None", "null"]
        }

    response_document["id"] = re.sub(r'[' + string.punctuation + ']', '-',
                                     url.split("://")[-1]) + '_' + hashlib.md5(
        bytes(str(datetime.datetime.now()),
              encoding="utf8")).hexdigest()[:5]
    response_document = json.loads(json.dumps(response_document))

    response_document = sanitize_values(response_document)

    response_document = sanitize_nested_values(response_document)

    return response_document


def run_tasks(urls_to_scrape, model_config):
    tasks = []
    for url, metadata in urls_to_scrape.items():
        tasks.append(main(url, metadata, model_config))
    # results = await asyncio.gather(*tasks)
    json.dump(tasks, open("result.json", "w"), indent=4)
    for i in tasks:
        try:
            upsert_document(INDEX, i["id"], i)
            print("URL: ", i["url"], "|", i["id"])
        except:
            json.dump(i, open("error_llm_results.json", "w"), indent=4)
            raise
    return tasks


if __name__ == '__main__':
    urls_to_scrape = os.getenv("SCRAPE_CONFIG_PATH")
    model_config = os.getenv("MODEL_CONFIG_PATH")
    # assert urls_to_scrape and model_config, \
    #     f"both urls_to_scrape and model_config should be present. Found {urls_to_scrape} and {model_config}"
    # urls_to_scrape = json.load(open(urls_to_scrape))
    # model_config = json.load(open(model_config))
    # links = {}
    # for link in urls_to_scrape:
    #     scrape_conf = {link: urls_to_scrape[link]}
    #     results = run_tasks(scrape_conf, model_config)
    #     links[link] = results[0]
    #     # print(results)
    # # pickle.dump(results, open("json_results.pkl", "wb"))
    # json.dump(links, open("all_link_results.json", "w"), indent=4)

    model_config = config = {
        "llm": {
            "model": "gpt-4o-mini",
            "model_provider": "openai",
            "temperature": 0.0,
            # "format": "json",
            # "base_url":
            # "http://localhost:11434",  # Not needed for online models/services
            # "model_tokens": 8192,
            # "chunk_size": 8192,
        },
        "embeddings": {
            "model": "text-embedding-3-small",
            # "model_provider": "openai",
            # "base_url":
            # "http://localhost:11434",  # Not needed for online models/services
            # "model_tokens": 2048,
            # "chunk_size": 2048,
        },
        "library": "BeautifulSoup"
    }
    urls_to_scrape = {
        "link": {
            "datapoints": [
                "title", "author", "authors", "published/created date", "created_at",
                "topics",
            ]
        }
    }
    # loop = asyncio.get_event_loop()
    # results = loop.run_until_complete(
    links = {
        # "https://bitcointalk.org/index.php?topic=935898.0": [],
        # "https://bitcoincore.reviews/": [],
        # "https://ark-protocol.org/": [],
        # "https://armantheparman.com/op_return/":[],
        # "https://blog.casa.io/bitcoin-multisig-hardware-signing-performance/": [],
        # "https://bitcoinmagazine.com/": [],
        # "https://blog.lopp.net/who-controls-bitcoin-core/": [],
        # "https://blog.lopp.net/empty-bitcoin-blocks-full-mempool": [],
        # "https://bitcoin.stackexchange.com/questions/122300/error-validating-transaction-transaction-orphaned-missing-reference-testnet": [],
        # "https://bitcoinops.org/en/newsletters/2024/08/09/": [],

        # "https://blog.lopp.net/how-many-bitcoin-seed-phrases-are-only-one-repeated-word/": [],
        # "https://armantheparman.com/": [],
        # "https://armantheparman.com/parmanvault/": [],
        # "https://bitcoinmagazine.com/culture/breaking-down-dirty-coin-the-documentary-that-shatters-bitcoin-mining-myths": [],
        # "https://bitcoinmagazine.com/business/river-a-bitcoin-brokerage-built-from-the-ground-up": [],
        # "https://www.podpage.com/citadeldispatch/citadel-dispatch-e43-bitcoin-for-beginners-with-bitcoinq_a/": [],
        # # "https://www.reddit.com/user/nullc/": [],
        # "https://public-sonic.fantom.network/address/0x5470cDA2Fb7200d372242b951DE63b9dC4A6a8A2": [],

        # "https://VEINTIUNO.world": [],

        # "https://bitcoin.stackexchange.com/questions/111395/what-is-the-weight-of-a-p2tr-input": [],
        # "https://docs.lightning.engineering/": [],

        # "https://www.lopp.net/bitcoin-information.html": [],
        # # "https://learnmeabitcoin.com": [],
        # # "https://en.bitcoin.it/": [],

        # "https://github.com/bitcoinbook/bitcoinbook": []
        # "https://veintiuno.world/evento/bitcoin-farmers-market-2025-03-23/": [],
        # "https://bitcoin.stackexchange.com/questions/123792/is-it-possible-to-spend-unconfirmed-utxo": [],
        # "https://stackoverflow.com/questions/2081586/web-scraping-with-python": [],
        # "https://aviation.stackexchange.com/questions/106435/is-there-any-video-of-an-air-to-air-missile-shooting-down-an-aircraft": [],
        "https://politics.stackexchange.com/questions/88817/why-does-russia-strike-electric-power-in-ukraine": []
    }

    for link in links:
        scrape_conf = {link: urls_to_scrape["link"]}
        if "stackexchange" in link or "stackoverflow" in link:
            scrape_conf[link]["datapoints"].extend([
                "question", "question content", "answers", "accepted_answer_indicator_exists", "accepted_answer",
                "highest_voted_ans",
                "comments", "user_statistics", ".Get full question content with all paragraphs.",
                "\nIf some answer or it's parent has classes like 'accepted-answer', 'js-accepted-answer', 'js-accepted-answer-indicator' or something similar, even in a parent div, then it is accepted answer\n. Get text from that whole div. Accepted answer is mandatory."
            ])
        results = run_tasks(scrape_conf, model_config)
        links[link] = results[0]
        # print(results)
    # pickle.dump(results, open("json_results.pkl", "wb"))
    json.dump(links, open("all_link_results.json", "w"), indent=4)