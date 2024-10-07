const readline = require('readline');
const { calculateScore } = require('./scoring');
const { getQuestions } = require('./questions');
const { askQuestion } = require('./user_io');

function startGame() {
    const questions = getQuestions();
    let score = 0;
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    let questionIndex = 0;

    function nextQuestion() {
        if (questionIndex < questions.length) {
            askQuestion(rl, questions[questionIndex], (answer) => {
                if (answer.toLowerCase() === questions[questionIndex].correctAnswer.toLowerCase()) {
                    score++;
                }
                questionIndex++;
                nextQuestion();
            });
        } else {
            rl.close();
            console.log(`Game Over! Your final score is: ${calculateScore(score, questions.length)}`);
        }
    }

    nextQuestion();
}

module.exports = { startGame };
