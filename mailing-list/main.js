const cheerio = require("cheerio");

const fs = require("fs");
const https = require("https");
const dotenv = require("dotenv");
const path = require("path");
dotenv.config();

const {
    index_documents,
    create_batches,
    checkDocumentExist
} = require("../common/elasticsearch-scraper/util");
const {
    log,
    count
} = require("console");

let URL = process.env.URL || "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/";
let NAME = process.env.NAME || "bitcoin";

if (URL === "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/") {
    NAME = "bitcoin";
} else if (URL === 'https://lists.linuxfoundation.org/pipermail/lightning-dev/') {
    NAME = "lightning";
}

console.log(
    `NAME: ${NAME}\nURL: ${URL}`
);


const MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
];

const days = process.env.DAYS_TO_SUBTRACT || 15;
let startDate = new Date();
startDate.setDate(startDate.getDate() - days);

let year = startDate.getUTCFullYear(); // Year to start scrapping with
let month = startDate.getUTCMonth(); // Month to start scrapping with


async function download_dumps() {
    if (!fs.existsSync(path.join(process.env.DATA_DIR, "mailing-list"))) {
        fs.mkdirSync(path.join(process.env.DATA_DIR, "mailing-list"), {
            recursive: true
        });
    }
    const agent = new https.Agent({
        keepAlive: true
    });
    let consecutive_errors = 0;
    while (true) {
        console.log(`Downloading ${year}-${MONTHS[month]}...`);
        const url = URL + year + "-" + MONTHS[month] + "/date.html";
        const response = await fetch(url);
        const text = await response.text();
        const $ = cheerio.load(text);

        // Get first ul element
        const uls = $("ul");
        if (uls.length === 0) {
            console.log("No more data");
            consecutive_errors++;
            if (consecutive_errors >= 6)
                break;

            month++;
            if (month >= MONTHS.length) {
                month = 0;
                year++;
            }
            continue;
        }

        const ul = uls[1];

        // Get all li elements
        const links = $("li a", ul);
        const batches = create_batches(links, 30);

        for (const batch of batches) {
            await Promise.all(
                Array.from(batch).map(async (link) => {
                    const href = link.attribs.href;
                    if (!href) return;

                    const fileName = path.join(
                        process.env.DATA_DIR,
                        "mailing-list",
                        `${year}-${MONTHS[month]}-${href}`
                    );
                    if (fs.existsSync(fileName)) {
                        console.log(`Skipping ${fileName}`);
                        return;
                    }

                    const u = URL + year + "-" + MONTHS[month] + "/" + href;
                    console.log(`Downloading ${u}`);
                    const response = await fetch(u, {
                        agent
                    });
                    const text = await response.text();

                    fs.writeFileSync(fileName, text);
                })
            );
        }

        month++;
        if (month >= MONTHS.length) {
            month = 0;
            year++;
        }
    }
}

function parse_dumps() {
    const documents = [];
    const files = fs.readdirSync(path.join(process.env.DATA_DIR, "mailing-list"));
    for (const file of files) {
        const text = fs.readFileSync(
            path.join(process.env.DATA_DIR, "mailing-list", file),
            "utf8"
        );
        const $ = cheerio.load(text);

        console.log(`Parsing ${file}...`);

        const author = $("b").first().text();
        const title = $("h1").first().text()
            .replace("[Bitcoin-development] ", "")
            .replace("[bitcoin-dev] ", "")
            .replace("[Lightning-dev]", "")
            .replace("[lightning-dev] ", "")
            .replace("\t", " ")
            .trim();
        const body = $("pre").first().text();
        const date = new Date($("I").first().text().replace("  ", " "));

        // remove any html in body
        const bodyText = body.replace(/<[^>]*>?/gm, "");

        const fileDate = file.split("-")[0] + "-" + file.split("-")[1];
        const fileName = file.split("-")[2];
        const document = {
            id: "mailing-list-" + NAME + '-' + file.replace(".html", ""),
            authors: [author],
            title,
            body: bodyText,
            body_type: "raw",
            created_at: date,
            domain: URL,
            url: `${URL}${fileDate}/${fileName}`,
        };

        documents.push(document);
    }

    return documents;
}

function findEarliestTimestamp(documents, title) {
    const earliest = documents
        .filter((d) => d.title === title)
        .sort((a, b) => a.created_at - b.created_at)[0];
    return earliest.created_at;
}

async function main() {
    await download_dumps();

    if (!fs.existsSync(path.join(process.env.DATA_DIR, "mailing-list"))) {
        console.log("Please download the data first");
        process.exit(1);
    }

    let parsed_dumps = parse_dumps();
    let documents = [];
    fs.writeFileSync(
        path.join(process.env.DATA_DIR, "mailing-list", "documents.json"),
        JSON.stringify(parsed_dumps)
    );

    
    if (
        fs.existsSync(
            path.join(process.env.DATA_DIR, "mailing-list", "documents.json")
        )
    ) {
        documents = JSON.parse(
            fs.readFileSync(
                path.join(process.env.DATA_DIR, "mailing-list", "documents.json"),
                "utf8"
            )
        );
    }
    console.log(`Found ${documents.length} documents`);

    let threads = {};
    console.log('Filtering existing documents...');
    for (let i = 0; i < documents.length; i++) {
        const document = documents[i];
        let isExist = await checkDocumentExist(document.id);
        if (isExist) {
            documents.splice(i, 1);
        } else {
            if (!threads[document.title]) {
                threads[document.title] = {
                    id: document.id,
                    date: findEarliestTimestamp(documents, document.title),
                    url: document.url,
                };
            }

            if (threads[document.title].id === document.id) {
                document.type = "original_post";
            } else {
                document.type = "reply";
                document.thread_url = threads[document.title].url;
            }
        }
    }

    console.log(`Inserting ${documents.length}...`);
    await index_documents(documents);
}


main();
