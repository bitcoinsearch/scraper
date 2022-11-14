const cheerio = require("cheerio");

const fs = require("fs");
const https = require("https");
const dotenv = require("dotenv");
const path = require("path");
dotenv.config();

const { index_documents, create_batches } = require("../common/util");

const URL = "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/";

const START_YEAR = 2011;
const START_MONTH = 5; // June

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

let year = START_YEAR;
let month = START_MONTH;

async function download_dumps() {
    if (!fs.existsSync(path.join(process.env.DATA_DIR, "mailing-list"))) {
        fs.mkdirSync(path.join(process.env.DATA_DIR, "mailing-list"));
    }
    const agent = new https.Agent({ keepAlive: true });
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
            break;
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
                    const response = await fetch(u, { agent });
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
        const title = $("h1").first().text().replace("[Bitcoin-development] ", "").replace("[bitcoin-dev] ", "");
        const body = $("pre").first().text();
        const date = new Date($("I").first().text().replace("  ", " "));

        // remove any html in body
        const bodyText = body.replace(/<[^>]*>?/gm, "");

        const fileDate = file.split("-")[0] + "-" + file.split("-")[1];
        const fileName = file.split("-")[2];
        const document = {
            id: "mailing-list-" + file.replace(".html", ""),
            author,
            title,
            body: bodyText,
            created_at: date,
            domain: "https://lists.linuxfoundation.org/pipermail/bitcoin-dev/",
            url: `https://lists.linuxfoundation.org/pipermail/bitcoin-dev/${fileDate}/${fileName}`,
        };

        documents.push(document);
    }

    return documents;
}

async function main() {
    await download_dumps();

    if (!fs.existsSync(path.join(process.env.DATA_DIR, "mailing-list"))) {
        console.log("Please download the data first");
        process.exit(1);
    }

    let documents = [];
    if (
        !fs.existsSync(
            path.join(process.env.DATA_DIR, "mailing-list", "documents.json")
        )
    ) {
        documents = parse_dumps();
        fs.writeFileSync(
            path.join(process.env.DATA_DIR, "mailing-list", "documents.json"),
            JSON.stringify(documents)
        );
    } else {
        documents = JSON.parse(
            fs.readFileSync(
                path.join(process.env.DATA_DIR, "mailing-list", "documents.json"),
                "utf8"
            )
        );
    }
    console.log(`Found ${documents.length} documents`);

    await index_documents(documents);
}


main();