function urlParser() {
    const sheetName = 'data';
  
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
    const dataRange = sheet.getDataRange();
    const dataValues = dataRange.getValues();
  
    const headers = dataValues.shift();
  
    // Find the index of the URL column and the "domain" column
    const urlColumnIndex = headers.indexOf('URL');
    const toDomainColumnIndex = headers.indexOf('To Domain');
  
    dataValues.forEach((row, rowIndex) => {
      const postData = {};
      headers.forEach((header, index) => {
        const value = row[index];
        if (header === 'created_at') {
        } else if (value !== '' && value !== null) {
          postData[header] = value;
        }
      });

      const url = row[urlColumnIndex];
      const domain = parseURL(url);
      if (domain) {
        sheet.getRange(rowIndex + 2, toDomainColumnIndex + 1).setValue(domain);
      }
  
      // ... rest of the code for posting to webhook
    });
  }
  