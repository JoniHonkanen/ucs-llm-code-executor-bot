function calculateScore(correctAnswers, totalQuestions) {
    return `${correctAnswers} out of ${totalQuestions}`;
}

module.exports = { calculateScore };
