function askQuestion(rl, question, callback) {
    rl.question(`${question.question} `, (answer) => {
        callback(answer);
    });
}

module.exports = { askQuestion };
