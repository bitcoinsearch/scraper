const { Client } = require('@elastic/elasticsearch')
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
        auth: { username, password }
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

                if (bulkResponse.errors) {
                    const erroredDocuments = []
                    // The items array has the same order of the dataset we just indexed.
                    // The presence of the `error` key indicates that the operation
                    // that we did for the document has failed.
                    bulkResponse.items.forEach((action, i) => {
                      const operation = Object.keys(action)[0]
                      if (action[operation].error) {
                        erroredDocuments.push({
                          // If the status is 429 it means that you can retry the document,
                          // otherwise it's very likely a mapping error, and you should
                          // fix the document before to try it again.
                          status: action[operation].status,
                          error: action[operation].error,
                          operation: operations[i * 2],
                          document: operations[i * 2 + 1]
                        })
                      }
                    })
                    console.log(erroredDocuments);
                  }
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