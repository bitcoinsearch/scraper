const { Client } = require("@elastic/elasticsearch");
function create_batches(objects, size) {
    const batches = [];
    for (let i = 0; i < objects.length; i += size) {
        const batch = [];
        for (let j = 0; j < size; j++) {
            if (objects[i + j]) {
                batch.push(objects[i + j]);
            }
        }

        batches.push(batch);
    }

    return batches;
}

async function fetch_with_retry(url, options) {
    let success = false;
    let response = null;
    while (!success) {
        try {
            response = await fetch(url, options);
            success = true;
        } catch (e) {
            console.log(e);
            console.log("Retrying in 10 seconds...");
            await new Promise((resolve) => setTimeout(resolve, 1000 * 10));
        }
    }

    return response;
}

async function index_documents(documents) {
    let cloud_id = process.env.CLOUD_ID;
    let username = process.env.USERNAME;
    let password = process.env.PASSWORD;
    const client = new Client({
        cloud: { id: cloud_id },
        auth: { username, password },
    });

    const batches = create_batches(documents, 50);
    let elapsed = 0;
    let done = 0;
    for (const batch of batches) {
        let success = false;
        let start_time = new Date();
        console.log(`Indexing ${batch.length} documents...`);

        while (!success) {
            try {
                const operations = batch.flatMap(doc => [{ index: { _index: process.env.INDEX } }, doc])
                const bulkResponse = await client.bulk({ refresh: true, operations })
                console.log(bulkResponse);

                success = true;
                done += batch.length;
            } catch (e) {
                console.log(e);
                console.log("Retrying in 10 seconds...");
                await new Promise((resolve) => setTimeout(resolve, 1000 * 10));
            }
        }

        let end_time = new Date();
        let seconds = Math.round((end_time - start_time) / 1000);
        console.log(`Took ${seconds} seconds`);

        elapsed += seconds;

        console.log(`Remaining time: ${Math.round((elapsed / done) * (documents.length - done))} seconds`);
    }

    console.log("Done");
}

module.exports = {
    create_batches,
    index_documents,
    fetch_with_retry
};
