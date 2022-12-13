const fs = require('fs');
const dotenv = require('dotenv');
const AdmZip = require('adm-zip');
const path = require('path');
const request = require('request');
const yaml = require('js-yaml');
const { basename } = require('path');
const marked = require('marked');
const { create_batches, index_documents } = require('../common/util');

dotenv.config();

const folder_name = "bitcoinops.github.io-master";

async function download_repo() {
    const URL = "https://github.com/bitcoinops/bitcoinops.github.io/archive/refs/heads/master.zip";
    const dir = path.join(process.env.DATA_DIR, "bitcoinops");
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
    });

    const frontMatterObj = yaml.load(frontMatter);
    const document = {
        id: "bitcoinops-" + (topic ? basename(path, '.md') : frontMatterObj.slug),
        title: frontMatterObj.title,
        body: parsedBody,
        body_type: "markdown",
        created_at: new Date(basename(path).split('-').slice(0, 3).join('-')),
        domain: "https://bitcoinops.org/en/",
        url: topic ? `https://bitcoinops.org/en/topics/${basename(path, '.md')}` : `https://bitcoinops.org${frontMatterObj.permalink}`,
        type: topic ? 'topic' : frontMatterObj.type,
        language: frontMatterObj.lang,
        authors: ["bitcoinops"],
    };

    return document;
}

function parse_topics() {
    const documents = [];
    const dir = path.join(process.env.DATA_DIR, "bitcoinops", folder_name, "_topics/en");
    const files = fs.readdirSync(dir);
    for (const file of files) {
        console.log(`Parsing ${path.join(dir, file)}...`);
        documents.push(parse_post(path.join(dir, file), true));
    }

    return documents;
}

async function main() {
    await download_repo();
    const dir = path.join(process.env.DATA_DIR, "bitcoinops", folder_name, "_posts", "en");
    const documents = parse_posts(dir).concat(parse_topics());

    console.log(`Parsed ${documents.length} documents`);

    await index_documents(documents);
}

main();