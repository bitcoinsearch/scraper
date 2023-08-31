import {OpenAIEmbeddings} from 'langchain/embeddings/openai';
import {ElasticVectorSearch} from "langchain/vectorstores/elasticsearch";
import {RecursiveCharacterTextSplitter} from "langchain/text_splitter";
import {Document} from "langchain/document";
import {v4} from 'uuid';

const {Client} = require("@elastic/elasticsearch");

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

async function upload_batches_to_vectorstore(batches, client) {
    const chunk_size = parseInt(process.env.CHUNK_SIZE, 10);
    const clientArgs = {
        client,
        indexName: process.env.VECTORSTORE_INDEX
    }
    const splitter = new RecursiveCharacterTextSplitter({
        chunkSize: chunk_size,
        chunkOverlap: Math.floor(chunk_size / 10),
    });
    const documents = await Promise.all(batches.flatMap(async (x) => {
        const {body, ...rest} = x;
        const id_: string = rest.pop('id');
        const chunks = await splitter.splitText(body);
        return chunks.map((doc, i) => new Document({
            pageContent: doc,
            metadata: {
                ...rest,
                parent_id: id_,
                chunk_no: i + 1,
                id: id_ + '_' + v4()
            }
        }))
    }));
    const embeddings = new OpenAIEmbeddings({openAIApiKey: process.env.OPENAI_API_KEY});
    const vectorstore = new ElasticVectorSearch(embeddings, clientArgs);
    const document_ids = documents.map(({metadata}) => metadata.id)
    const ids = await vectorstore.addDocuments(documents, {ids: document_ids});
    console.log("Uploaded to vectorstore");
    // console.log("Document Chunk Ids: ", ids);
}


async function index_documents(documents) {
    let cloud_id = process.env.CLOUD_ID;
    let username = process.env.USERNAME;
    let api_key = process.env.USER_PASSWORD;
    const client = new Client({
        cloud: {id: cloud_id},
        auth: {apiKey: api_key}
    });

    const batches = create_batches(documents, 50);
    await upload_batches_to_vectorstore(batches, client);
    let elapsed = 0;
    let done = 0;
    for (const batch of batches) {
        let success = false;
        let start_time = new Date();
        console.log(`Indexing ${batch.length} documents...`);

        while (!success) {
            try {
                const operations = batch.flatMap(doc => [{index: {_index: process.env.INDEX}}, doc])
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

module.exports = {
    create_batches,
    index_documents,
    fetch_with_retry
};
