const fs = require('fs');
const dotenv = require('dotenv');
const AdmZip = require('adm-zip');
const path = require('path');
const request = require('request');
const yaml = require('js-yaml');
const marked = require('marked');
const { index_documents } = require('../common/util');
const md5 = require('md5');

dotenv.config();

const folder_name = "bitcointranscripts-master";

async function download_repo() {
    const URL = "https://github.com/bitcointranscripts/bitcointranscripts/archive/refs/heads/master.zip";
    const dir = path.join(process.env.DATA_DIR, "bitcointranscripts");
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
            if (file === '.github') continue;
            documents = documents.concat(parse_posts(path.join(dir, file)));
            continue
        }

        if (dir === path.join(process.env.DATA_DIR, "bitcointranscripts", folder_name)) continue;
        if (file.startsWith('_')) continue;
        // Skip if file ends with .??.md (skip translations)
        if (file.match(/\.([a-z][a-z])\.md$/)) continue;
        if (!file.endsWith('.md')) continue;

        console.log(`Parsing ${path.join(dir, file)}...`);
        const document = parse_post(path.join(dir, file));
        documents.push(document);
    }
    return documents;
}

function parse_post(p_path) {
    const content = fs.readFileSync(p_path, 'utf8');

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

    const parsedBody = marked.lexer(body.substr(0, 90000)).map((token) => {
        return ({
            type: token.type,
            text: token.text,
        })
    }).filter((token) => {
        return token.type !== 'space';
    });

    const pathWithoutExtension = p_path.replace('.md', '');
    const frontMatterObj = yaml.load(frontMatter);
    const id = md5(pathWithoutExtension.replace(path.join(process.env.DATA_DIR, "bitcointranscripts", folder_name), '').replaceAll("/", "-")).substring(0, 20);
    const document = {
        id: "bitcointranscripts-" + id,
        title: frontMatterObj.title,
        body: parsedBody,
        created_at: new Date(frontMatterObj.date),
        domain: "https://btctranscripts.com/",
        url: `https://btctranscripts.com${pathWithoutExtension.replace(path.join(process.env.DATA_DIR, "bitcointranscripts", folder_name), '')}`,
        categories: frontMatterObj.categories,
        tags: frontMatterObj.tags,
        media: frontMatterObj.media,
        authors: frontMatterObj.speakers,
        transcript_by: frontMatterObj.transcript_by,
    };

    return document;
}

async function main() {
    await download_repo();
    const dir = path.join(process.env.DATA_DIR, "bitcointranscripts", folder_name);
    const documents = parse_posts(dir);

    console.log(`Parsed ${documents.length} documents`);
    await index_documents(documents);
}

main();