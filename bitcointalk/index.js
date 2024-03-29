
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');
const dotenv = require('dotenv');
dotenv.config();

const {index_documents, fetch_with_retry,} = require('../common/util');
const {
    checkDocumentExist,
    create_document,
    delete_document_if_exist,
    document_view
} = require('../common/elasticsearch-scraper/util')

const BOARD_URL = 'https://bitcointalk.org/index.php?board=6.';

authors = ['achow101', 'kanzure', 'Sergio_Demian_Lerner', 'Nicolas Dorier', 'jl2012', 'Peter Todd', 'Gavin Andresen', 'adam3us', 'Pieter Wuille', 'Meni Rosenfeld', 'Mike Hearn', 'wumpus', 'Luke-Jr', 'Matt Corallo', 'jgarzik', 'andytoshi', 'satoshi', 'Cdecker', 'TimRuffing', 'gmaxwell'];

async function fetch_all_topics() {
    if (!fs.existsSync(path.join(process.env.DATA_DIR, 'bitcointalk'))) {
        fs.mkdirSync(path.join(process.env.DATA_DIR, 'bitcointalk'), {recursive: true});
    }
    let offset = 0;
    const topics = [];
    while (true) {
        console.log(`Downloading page ${offset / 40}...`);
        const url = BOARD_URL + offset;
        let success = false;
        let tops = [];
        while (!success) {
            const response = await fetch(url);
            const text = await response.text();
            if (response.status !== 200) {
                console.log(`Error ${response.status} downloading page ${offset / 20}`);
                await new Promise(resolve => setTimeout(resolve, 2000));
                continue;
            }
            success = true;
            const $ = cheerio.load(text);

            const links = $('tr > td > span > a');
            for (const link of links) {
                const href = $(link).attr('href');
                if (!href.startsWith("https://bitcointalk.org/index.php?topic=") || $(link).attr('class') !== undefined) {
                    continue;
                }
                tops.push(href);
            }

            offset += 40;
        }

        topics.push(...tops);

        if (tops.length !== 40) {
            console.log("No more data");
            break;
        }

        await new Promise(resolve => setTimeout(resolve, 800));
    }

    return topics;
}

async function get_documents_from_post(url) {
    const response = await fetch_with_retry(url);
    const text = await response.text();
    const $ = cheerio.load(text);

    if (response.status >= 500 || response.status === 403) {
        console.log(`Error ${response.status} downloading ${url}`);
        await new Promise(resolve => setTimeout(resolve, 10000));
        return get_documents_from_post(url);
    }

    let urls = $('a.navPages').toArray().map(a => $(a).attr('href'))
    urls = [...new Set(urls)];

    // #quickModForm > table:nth-child(1)
    const table = $('#quickModForm > table:nth-child(1)');
    const rows = table.find('tr');
    const firstTrClass = $(rows[0]).attr('class');

    const trList = table.find(`tr.${firstTrClass}`);
    console.log(`Found ${trList.length} posts in ${url}`);

    if (trList.length === 0) {
        console.log(text);
    }

    const documents = [];

    for (const tr of trList) {
        const author = $(tr).find('.poster_info > b > a').text();

        if (!authors.includes(author)) {
            continue;
        }
        console.log(`post by : ${author}`)

        // text without title attribute
        let date = $(tr).find('.td_headerandpost .smalltext > .edited').text();
        if (date === '') {
            date = $(tr).find('.td_headerandpost .smalltext').text();
        }

        // remove text after "Merited by"
        const meritedIndex = date.indexOf('Merited by');
        if (meritedIndex !== -1) {
            date = date.substring(0, meritedIndex);
        }

        if (date.startsWith('Today at')) {
            date = date.replace('Today at', new Date().toLocaleDateString());
        }

        const url = $(tr).find('.td_headerandpost .subject > a').attr('href');
        const title = $(tr).find('.td_headerandpost .subject > a').text();
        let body = $(tr).find('.td_headerandpost .post');
        let messageNumber = $(tr).find('.td_headerandpost .message_number').text();
        // remove div with class 'quoteheader' and 'quote'
        body.find('.quoteheader').remove();
        body.find('.quote').remove();
        body = body.text();

        const dateJs = new Date(date);
        const indexed_at = new Date().toISOString();

        const id = url.substring(url.indexOf('#msg') + 4);

        const document = {
            authors: [author],
            body,
            body_type: 'raw',
            domain: 'https://bitcointalk.org/',
            url,
            title,
            id: 'bitcointalk-' + id,
            created_at: dateJs,
            indexed_at: indexed_at,
            type: messageNumber === "#1" ? "topic" : "post",
        }

        documents.push(document);
    }
    console.log(`Filtered ${documents.length} posts in ${url}`);
    return {documents, urls};
}

async function fetch_posts(url) {
    const resp = await get_documents_from_post(url);
    const documents = resp.documents;

    const urls = resp.urls;

    for (const url of urls) {
        console.log(`Downloading ${url}...`);
        const resp = await get_documents_from_post(url);
        documents.push(...resp.documents);

        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    return documents;
}

async function main() {
    // store in file if not already there
    const filename = path.join(process.env.DATA_DIR, 'bitcointalk', 'topics.json');
    let topics = [];
    if (!fs.existsSync(filename)) {
        topics = await fetch_all_topics();
        fs.writeFileSync(filename, JSON.stringify(topics));
    } else {
        const data = fs.readFileSync(filename, 'utf8');
        topics = JSON.parse(data);
    }

    console.log(`Found ${topics.length} topics`);
    let count = 0;
    const start_index = process.env.START_INDEX ? parseInt(process.env.START_INDEX) : 0;
    for (let i = start_index; i < topics.length; i++) {
        const topic = topics[i];
        console.log(`Processing ${i + 1}/${topics.length}`);
        const documents = await fetch_posts(topic);

        for (let i = 0; i < documents.length; i++) {
            const document = documents[i];

//            // delete posts with previous logic where '_id' was set on its own and replace them with our logic
//            const deleteId = await delete_document_if_exist(document.id)

            const viewResponse = await document_view(document.id);
            if (!viewResponse) {
                const createResponse = await create_document(document);
                count++;
            }

        }

    }
    console.log(`Inserted ${count} new documents`);
}

main().catch(console.error);
