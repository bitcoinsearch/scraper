//This script send data directly to elastic search (ES) index.
//To run copy the script to the sheet's appscript that needs to be ingested to ES.

function postSheetDataToElasticsearch() {
  const sheetName = 'sheet1';
  const elasticsearchUrl = ' ';
  const apiKey = ' ';

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  const dataRange = sheet.getDataRange();
  const dataValues = dataRange.getValues();

  const headers = dataValues.shift();

  dataValues.forEach((row, rowIndex) => {
    const postData = {};
    headers.forEach((header, index) => {
      const value = row[index];
      if (header === 'indexed_at') {
        postData[header] = new Date().toISOString(); // Set the current date and time
      } else if (header === 'Id') {
        postData[header] = 'googlesheet-' + (rowIndex + 1); // Set the id column as "googlesheet-1", "googlesheet-2", ...
      } else if (header === 'tags') {
        postData[header] = [value.toLowerCase().trim()]; // Convert tags to lowercase
      } else if (header === 'created_at') {
        if (value instanceof Date && !isNaN(value)) {
          postData[header] = value.toISOString();
        } else if (typeof value === 'string' && value.trim() !== '') {
          const date = new Date(value);
          if (!isNaN(date)) {
            postData[header] = date.toISOString();
          } else {
            postData[header] = new Date().toISOString(); // Assign current date if the value is an invalid string
          }
        } else {
          postData[header] = new Date().toISOString(); // Assign current date if the value is empty or not a valid date
        }
      } else if (value !== '' && value !== null) {
        if (header === 'authors' || header === 'categories') {
          postData[header] = [value.trim()];
        } else {
          postData[header] = value;
        }
      }
    });

    const options = {
      method: 'post',
      contentType: 'application/json',
      muteHttpExceptions: true,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'ApiKey ' + apiKey
      },
      payload: JSON.stringify(postData),
    };

    const response = UrlFetchApp.fetch(elasticsearchUrl, options);
    const responseCode = response.getResponseCode();
    if (responseCode >= 200 && responseCode !== 400) {
      Logger.log('Data sent to Elasticsearch (row ' + (rowIndex + 1) + '). Response code: ' + responseCode);
    } else if (responseCode >= 400) {
      Logger.log('Could not send data to Elasticsearch (row ' + (rowIndex + 1) + '). Response code: ' + responseCode);
    } else {
      Logger.log('Execution complete');
    }

    // Utilities.sleep(); // Pause execution for 2 seconds
  });
}
