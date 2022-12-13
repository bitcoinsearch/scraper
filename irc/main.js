const path = require('path');
const dotenv = require('dotenv');
const fs = require('fs');
const request = require('request');
const { create_batches, index_documents } = require('../common/util');
dotenv.config();

const URL = "https://bitcoin-irc.chaincode.com/bitcoin-core-dev/";
async function download_dumps() {

    const START_YEAR = 2015;
    const START_MONTH = 9;
    const START_DAY = 30;

    let year = START_YEAR;
    let month = START_MONTH;
    let day = START_DAY;

    const dir = path.join(process.env.DATA_DIR, "bitcoin-core-dev");
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir);
    }

    const requestedLogs = [];

    while (true) {
        const yearStr = year.toString().padStart(4, '0');
        const monthStr = month.toString().padStart(2, '0');
        const dayStr = day.toString().padStart(2, '0');

        const file = path.join(dir, `${yearStr}-${monthStr}-${dayStr}.txt`);
        if (fs.existsSync(file)) {
            console.log(`Already downloaded ${file}`);
        } else {
            requestedLogs.push(`${yearStr}-${monthStr}-${dayStr}`);
        }

        // Increment date
        day++;
        if (day > 31) {
            day = 1;
            month++;
        }
        if (month > 12) {
            month = 1;
            year++;
        }

        // Check if we've reached the current date
        const now = new Date();
        if (year > now.getFullYear() || (year === now.getFullYear() && month > now.getMonth() + 1) || (year === now.getFullYear() && month === now.getMonth() + 1 && day > now.getDate())) {
            break;
        }
    }

    const batches = create_batches(requestedLogs, 100);
    for (const batch of batches) {
        console.log(`Fetching ${batch.length} logs...`);
        await Promise.all(batch.map(async (date) => {
            console.log(`Fetching ${date}...`);
            const url = `${URL}${date}.txt`;
            const file = path.join(dir, `${date}.txt`);
            const response = await fetch(url);
            const txt = await response.text();

            fs.writeFileSync(file, txt);
        }));
    }

    console.log("Done downloading dumps");
}

function parse_log(file) {
    const documents = [];
    const lines = fs.readFileSync(file).toString().split("\n");
    for (const line of lines) {
        const date = new Date(line.substring(0, 16));
        const message = line.substring(17);
        if (!message.startsWith("<")) {
            continue;
        }

        const username = message.substring(1, message.indexOf(">")).replace(" ", "");
        if (username === "bitcoin-git" || username.startsWith("GitHub")) {
            continue;
        }

        const body = message.substring(message.indexOf(">") + 1).trim();

        documents.push({
            id: `bitcoin-core-dev-${username}-${date.getTime()}`,
            created_at: date,
            authors: [username],
            body: body,
            domain: URL,
            url: `${URL}${file.substring(file.lastIndexOf("/") + 1)}`,
            url_scheme: "https",
        });
    }

    return documents;
}

function parse_logs() {
    const dir = path.join(process.env.DATA_DIR, "bitcoin-core-dev");
    let documents = [];
    const files = fs.readdirSync(dir);
    for (const file of files) {
        documents = documents.concat(parse_log(path.join(dir, file)));
    }

    return documents;
}

async function main() {
    await download_dumps();

    const documents = parse_logs();
    console.log(`Parsed ${documents.length} documents`);

    await index_documents(documents);
}

main();