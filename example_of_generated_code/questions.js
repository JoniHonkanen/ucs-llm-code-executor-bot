const fs = require('fs');
const path = require('path');

function getQuestions() {
    const filePath = path.join(__dirname, 'questions.json');
    const data = fs.readFileSync(filePath);
    return JSON.parse(data);
}

module.exports = { getQuestions };
