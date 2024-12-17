import os
import re
import json
import traceback
import tiktoken
import numpy as np
import inspect
from dotenv import load_dotenv

# https://api.python.langchain.com/en/latest/text_splitter/langchain_experimental.text_splitter.SemanticChunker.html
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI

from scraper.models import ScrapedDocument
from scraper.processors.base_processor import BaseProcessor
from scraper.registry import processor_registry


@processor_registry.register("semantic_chunking")
class SemanticChunkingProcessor(BaseProcessor):
    def __init__(self):
        super().__init__()
        self.params = self.load_processor_params()

    def load_processor_params(self):
        """Load parameters for chunker, llm model names and other params"""
        # Default params
        params = {
            # Semantic chunking params (for SemanticChunker, from documentation)
            "breakpoint_threshold_type": "standard_deviation",
            "buffer_size": 4,
            "breakpoint_threshold_amount": 3,
            "sentence_split_regex": r'(?<=[\.\!\?\n])(\n?)\s+',
            # Openai models
            "oai_embedding_model": "text-embedding-3-small",  # Model for embedding
            "oai_gen_model": "gpt-4o-mini",  # Model used for generating titles
            # Other params
            "chunk_threshold": 6000,  # Chunk only if number of tokens larger than this
            "use_markdown_headers": True,  # Use markdown headers for splitting
            "max_chunk_size": 6000,  # Max number of tokens in a chunk
            "generate_titles": False,  # Use LLM to generate titles for a chunk
        }
        param_file = os.getenv("SEMANTIC_CHUNKING_PARAMS", None)  # A Json file
        if param_file:
            params_ = json.load(open(param_file))
            for k,v in params_:
                params[k] = v
        if "sentence_split_regex" in params:
            params["sentence_split_regex"] = re.compile(params["sentence_split_regex"])
        return params

    def check_regex_parsable(self, full_body):
        found = re.findall(r'\n# .+\n\n', full_body)  # H1 headers
        found_h2 = re.findall(r'\n## .+\n\n', full_body)  # H2 headers
        if len(found) > 2 or len(found_h2) > 2:
            return True
        return False

    def chunk_text_by_markdown(self, text, found):
        """Chunk text based on markdown headers found in the text"""
        encoding = tiktoken.encoding_for_model(
            self.params.get("oai_embedding_model", "text-embedding-3-small"))
        delimiters = []
        found = [i.strip("\n") for i in found]
        delimiters.extend(found)
        text_chunks = re.split(r"(" + "|".join([re.escape(i) for i in found]) + ")",
                       text)
        text_chunks = [i for i in text_chunks if len(i)>0]
        regex_text_chunks = []
        for chunk in text_chunks:
            num_tokens = len(encoding.encode(chunk))
            if num_tokens > self.params.get("max_chunk_size", 6000):
                sub_chunk_delim = re.findall(r'\n## .+\n\n', chunk)
                sub_chunk_delim = [i.strip("\n") for i in sub_chunk_delim]
                delimiters.extend(sub_chunk_delim)
                if len(sub_chunk_delim)  > 0:
                    regex_text_chunks.extend(
                        re.split(r"(" + "|".join([re.escape(i) for i in sub_chunk_delim]) + ")",
                                 chunk))
                else:
                    regex_text_chunks.append(chunk)
            else:
                regex_text_chunks.append(chunk)
        # Combine delimiter string with next chunk
        text_chunks = []
        running_str = regex_text_chunks[0]
        for chunk in regex_text_chunks[1:]:
            if chunk in delimiters:
                text_chunks.append(running_str)
                running_str = chunk
            else:
                running_str += chunk
        text_chunks.append(running_str)
        text_chunks = [(i, "regex") for i in text_chunks]
        return text_chunks

    def chunk_text_semantically(self, text):
        """Chunk text based on markdown headers"""
        found = re.findall(r'\n# .+\n\n', text)  # H1 headers
        found_h2 = re.findall(r'\n## .+\n\n', text)  # H2 headers
        found_h3 = re.findall(r'\n### .+\n\n', text)  # H3 headers
        
        chunker_possible_params = dict(inspect.signature(SemanticChunker).parameters)
        chunker_params = {k:v for k,v in self.params.items() if k in chunker_possible_params}
        text_splitter = SemanticChunker(
            OpenAIEmbeddings(model=self.params.get("oai_embedding_model", "text-embedding-3-small")),
            **chunker_params)
        encoding = tiktoken.encoding_for_model(
            self.params.get("oai_embedding_model", "text-embedding-3-small"))
        
        # found = found + found_h2 + found_h3  # all become a new chunk
        if len(found) < 2 and len(found_h2) > 2:
            found = found_h2
        
        if self.params.get("use_markdown_headers", True) and len(found) > 2:
            text_chunks = self.chunk_text_by_markdown(text, found)
        else:
            text_chunks = text_splitter.split_text(text)
            text_chunks = [(re.sub(' +', ' ', re.sub(r'\n\s', '\n', i)), "semantic") for i in text_chunks]

        final_chunks = []
        for chunk, chunk_type in text_chunks:
            num_tokens = len(encoding.encode(chunk))
            if num_tokens > self.params.get("max_chunk_size", 6000):
                num_chunks = num_tokens // self.params.get("max_chunk_size", 6000) + bool(num_tokens % self.params.get("max_chunk_size", 6000))
                text_splitter_temp = SemanticChunker(
                    OpenAIEmbeddings(model=self.params.get("oai_embedding_model", "text-embedding-3-small")),
                    number_of_chunks=num_chunks)
                
                sub_chunks = text_splitter_temp.split_text(chunk)
                sub_chunks = [[i, "semantic_size"] for i in sub_chunks]
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append([chunk, chunk_type])
        return final_chunks

    def get_chunk_title(self, chunk):
        """Get chunk title using llm"""
        try:
            llm = ChatOpenAI(model_name=self.params.get("oai_gen_model", "gpt-4o-mini"))
            response = llm.invoke(
                f'Respond only with a suitable title for the following text: "{chunk}"')
            return response.content
        except Exception as e:
            traceback.print_exc()
        return None

    async def process(self, document: ScrapedDocument, chunker_params: dict = None) -> ScrapedDocument:
        body = document.body
        body_chunks = self.chunk_text_semantically(body)
        document.chunks = []
        prev_title = None
        prev_count = 1
        for idx, (chunk, chunk_type) in enumerate(body_chunks):
            chunk_title = None
            if chunk_type == "regex":
                chunk_title = chunk.strip("\n").split("\n")[0].strip("# ")
                prev_title = chunk_title
            elif chunk_type == "semantic_size" and prev_title is not None:
                chunk_title = prev_title + '-' + str(prev_count)
                prev_count += 1
            else:
                prev_title = None
                prev_count = 1
                chunk_title = None
                if self.params.get("generate_titles", False):
                    chunk_title = self.get_chunk_title(chunk)
            # Add chuks to input object
            document.chunks.append({
                "title": chunk_title,
                "id": f"{document.id}-chunk{idx}",
                "body": chunk
            })

        return document