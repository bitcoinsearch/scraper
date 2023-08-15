const fs = require('fs');
const dotenv = require('dotenv');
const AdmZip = require('adm-zip');
const path = require('path');
const request = require('request');
const yaml = require('js-yaml');
const marked = require('marked');
const { index_documents } = require('../common/elasticsearch-scraper/util');

dotenv.config();

const folder_name = "website-master";

async function download_repo() {
    const URL = "https://github.com/bitcoin-core-review-club/website/archive/refs/heads/master.zip";
    const dir = path.join(process.env.DATA_DIR, "pr-reviews");
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir);
    }
    
    if (fs.existsSync(path.join(dir, folder_name))) {
        console.log("Repo already downloaded");
        return;
    }

    console.log("Downloading repo...");

    // Download
    const file = path.join(dir, "master.zip");
    let downloaded = false;
    request.get(URL).pipe(fs.createWriteStream(file).on('finish', () => {
        console.log(`Downloaded ${URL} to ${file}`);

        // Unzip
        const zip = new AdmZip(file);
        zip.extractAllTo(dir, true);

        console.log(`Unzipped ${file} to ${dir}`);
        downloaded = true;
    }));

    // Wait for download to finish
    while (!downloaded) {
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}


function parse_posts(dir) {
    let documents = [];
    const files = fs.readdirSync(dir);
    for (const file of files) {
        if (fs.statSync(path.join(dir, file)).isDirectory()) {
            documents = documents.concat(parse_posts(path.join(dir, file)));
            continue
        }

        console.log(`Parsing ${path.join(dir, file)}...`);
        documents.push(parse_post(path.join(dir, file)));
    }
    return documents;
}

function parse_post(path, topic = false) {
    const content = fs.readFileSync(path, 'utf8');

    // remove any content that is between {% and %}
    const contentWithoutYaml = content.replace(/{%.*%}/gm, "");
    const lines = contentWithoutYaml.split("\n");

    let inFrontMatter = false;
    let inBody = false;
    let frontMatter = '';
    let body = '';
    for (const line of lines) {
        if (line.startsWith('---')) {
            if (inFrontMatter) {
                inFrontMatter = false;
                inBody = true;
                continue;
            }
            if (inBody) break;
            inFrontMatter = true;
            continue;
        }
        if (inFrontMatter) {
            frontMatter += line + '\n';
        } else if (inBody) {
            body += line + '\n';
        }
    }

    const parsedBody = marked.lexer(body).map((token) => {
        return ({
            type: token.type,
            text: token.text,
        })
    }).filter((token) => {
        return token.type !== 'space';
    });

    const stringRepresentation = parsedBody.map(obj => JSON.stringify(obj)).join(', ');
    const frontMatterObj = yaml.load(frontMatter);
    const document = {
        id: "pr-reviews-" + frontMatterObj.pr,
        title: frontMatterObj.title,
        body_formatted: stringRepresentation,
        body: body,
        body_type: "markdown",
        created_at: frontMatterObj.date,
        domain: "https://bitcoincore.reviews",
        url: "https://bitcoincore.reviews/" + frontMatterObj.pr,
        authors: frontMatterObj.authors,
        issue: frontMatterObj.pr,
        tags: frontMatterObj.components,
    };

    console.log(`created ${JSON.stringify(document, null, 2)}`);

    return document;
}

async function main() {
    await download_repo();
    const dir = path.join(process.env.DATA_DIR, "pr-reviews", folder_name, "_posts");
    const documents = parse_posts(dir)

    console.log(`Parsed ${documents.length} documents`);

    await index_documents(documents);
}

main();
