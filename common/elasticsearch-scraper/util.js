const {
    Client
} = require("@elastic/elasticsearch");

function create_batches(objects, size) {
    const batches = [];
    for (let i = 0; i < objects.length; i += size) {
        const batch = [];
        for (let j = 0; j < size; j++) {
            if (objects[i + j]) { // Timestamp the object upload to strictly order it
                const timestampedObj = {
                    ...objects[i + j],
                    indexed_at: new Date().toISOString()
                }
                batch.push(timestampedObj);
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
    let api_key = process.env.USER_PASSWORD
    const client = new Client({
        cloud: {
            id: cloud_id
        },
        auth: {
            apiKey: api_key
        }
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
                const operations = batch.flatMap(doc => [{
                    index: {
                        _index: process.env.INDEX
                    }
                }, doc])
                const bulkResponse = await client.bulk({
                    refresh: true,
                    pipeline: "avoid-duplicates",
                    operations
                })
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


async function checkDocumentExist(document_id) {
    let cloud_id = process.env.CLOUD_ID;
    let username = process.env.USERNAME;
    let api_key = process.env.USER_PASSWORD
    const client = new Client({
        cloud: {
            id: cloud_id
        },
        auth: {
            apiKey: api_key
        }
    });

    const bulkResponse = await client.count({
        index: process.env.INDEX,
        body: {
            query: {
                bool: {
                    must: [{
                        term: {
                            "id.keyword": document_id
                        }
                    }]
                }
            }
        }
    });
    return bulkResponse.count > 0;
}


async function create_document(document) {
    let cloud_id = process.env.CLOUD_ID;
    let username = process.env.USERNAME;
    let api_key = process.env.USER_PASSWORD
    const client = new Client({
        cloud: {
            id: cloud_id
        },
        auth: {
            apiKey: api_key
        }
    });

    try {
        const response = await client.index({
            index: process.env.INDEX,
            body: document,
            id: document.id,
            refresh: true // Ensure the document is immediately searchable
        });

        console.log(`Document processed :: result: ${response.result}, version: ${response._version}, id: ${response._id}`);
    } catch (error) {
        console.error(`Failed to process document :: id: ${document.id}, title: ${document.title}`);
        console.error(error);
    }
}


async function delete_document_if_exist(documentId) {
    let cloud_id = process.env.CLOUD_ID;
    let username = process.env.USERNAME;
    let api_key = process.env.USER_PASSWORD
    try {
        const client = new Client({
            cloud: {
                id: cloud_id
            },
            auth: {
                apiKey: api_key
            }
        });

        const searchResponse = await client.search({
            index: process.env.INDEX,
            body: {
                query: {
                    bool: {
                        must: [{
                            term: {
                                "id.keyword": documentId
                            }
                        }]
                    }
                }
            }
        });

        const hits = searchResponse.hits.hits;
        if (hits.length === 0) {
            console.info(`No documents found with source-id: ${documentId}`);
            return null;
        }

        const documentToDeleteId = hits[0]._id;
        console.info(`Document _id to delete: ${documentToDeleteId}`);

        const deleteResp = await client.delete({
            index: process.env.INDEX,
            id: documentToDeleteId
        });

        if (deleteResp.result === 'deleted') {
            console.info(`Deleted! '_id': '${documentToDeleteId}'`);
            return documentToDeleteId;
        } else {
            console.info("Failed to delete the document.");
            return null;
        }
    } catch (e) {
        console.error(e);
    }

}

async function document_view(docId) {
    try {
        let cloud_id = process.env.CLOUD_ID;
        let username = process.env.USERNAME;
        let api_key = process.env.USER_PASSWORD
        const client = new Client({
            cloud: {
                id: cloud_id
            },
            auth: {
                apiKey: api_key
            }
        });
        try {
            const response = await client.get({
                index: process.env.INDEX,
                id: docId,
            });
            return response;

        } catch (e) {
            if (e.meta && e.meta.statusCode === 404) {
                return false;
            } else {
                console.error(e)
            }

        }
    } catch (e) {
        console.error(e);
    }
}


async function update_document(document) {
    let cloud_id = process.env.CLOUD_ID;
    let api_key = process.env.USER_PASSWORD;
    const client = new Client({
        cloud: {
            id: cloud_id
        },
        auth: {
            apiKey: api_key
        }
    });

    try {
        // Check if the document exists
        const existsResponse = await client.exists({
            index: process.env.INDEX,
            id: document.id
        });

        if (existsResponse) {
            // If the document exists, update it with the new values
            const response = await client.update({
                index: process.env.INDEX,
                id: document.id,
                body: {
                    doc: document,
                    doc_as_upsert: true // If the document does not exist, create it
                },
                refresh: true // Ensure the document is immediately searchable
            });

            console.log(`Document updated :: result: ${response.result}, version: ${response._version}, id: ${response._id}`);
        } else {
            // If the document does not exist, create a new one
            const response = await client.index({
                index: process.env.INDEX,
                body: document,
                id: document.id,
                refresh: true // Ensure the document is immediately searchable
            });

            console.log(`Document created :: result: ${response.result}, version: ${response._version}, id: ${response._id}`);
        }
    } catch (error) {
        console.error(`Failed to process document :: id: ${document.id}, title: ${document.title}`);
        console.error(error);
    }
}

module.exports = {
    create_batches,
    index_documents,
    fetch_with_retry,
    checkDocumentExist,
    create_document,
    update_document,
    delete_document_if_exist,
    document_view,
};
