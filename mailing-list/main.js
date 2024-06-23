const cheerio = require("cheerio");

const fs = require("fs");
const https = require("https");
const dotenv = require("dotenv");
const path = require("path");

dotenv.config();

const {
    create_batches,
    update_document,
    document_view,
    create_document,
    delete_document_if_exist,
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
    `NAME: ${NAME} || URL: ${URL}`
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
const currentYear = new Date().getUTCFullYear();
const currentMonth = new Date().getUTCMonth();

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
             if (year === currentYear && month === currentMonth)
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
    let threads = {};
    for (const file of files) {
        const text = fs.readFileSync(
            path.join(process.env.DATA_DIR, "mailing-list", file),
            "utf8"
        );
        const $ = cheerio.load(text);

        console.log(`Parsing ${file}...`);

        let author = $("b").first().text();
        if(author.includes("at")){
            author = author.split("at")[0].trim()
        }else if(author.includes("At")){
            author = author.split("At")[0].trim()
        }
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
            thread_url: `${URL}${fileDate}/${fileName}`,
        };

        if (!threads[document.title]) {
            threads[document.title] = {
                id: document.id,
                thread_url: document.thread_url,
            };
        }

        if (threads[document.title].id === document.id) {
            document.type = "original_post";
        } else {
            document.type = "reply";
            document.url = threads[document.title].thread_url;
        }

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
    // console.log(`Found ${documents.length} documents`);

    console.log(`Filtering existing ${documents.length} documents... please wait...`);
    let count = 0;
    for (let i = 0; i < documents.length; i++) {
        const document = documents[i];

//        // delete posts with previous logic where '_id' was set on its own and replace them with our logic
//        const deleteId = await delete_document_if_exist(document.id)

        const response = await update_document(document);
        count++;
    }
    console.log(`Inserted ${count} new documents`);
}


main();
