# Developer Documentation

## Project Structure

The project is structured as follows:

```
quiz-game/
├── index.js
├── game.js
├── scoring.js
├── user_io.js
├── questions.js
├── questions.json
├── package.json
└── README.md
```

- **index.js**: The entry point of the quiz game that manages the flow of the game. It initializes the game, starts it, and displays the final score.
- **game.js**: Contains the game logic to handle questions and scoring. It reads questions from a JSON file, manages user input, calculates scores, and displays the final score.
- **scoring.js**: Contains functions to calculate the score of the quiz game.
- **user_io.js**: Handles user input and output to ask quiz questions and get user answers.
- **questions.js**: Contains utility functions. Currently, it only has a function to get questions from a JSON file.
- **questions.json**: A JSON file containing the quiz questions and their correct answers.
- **package.json**: Contains the project dependencies and their versions.

## Code Organization

- **index.js**: Imports the `startGame` function from `game.js` and starts the game.
- **game.js**: Imports necessary modules like `readline`, `calculateScore` from `scoring.js`, `getQuestions` from `questions.js`, and `askQuestion` from `user_io.js`. It manages the game loop and keeps track of the score.
- **scoring.js**: Exports a `calculateScore` function that calculates and formats the final score.
- **user_io.js**: Exports an `askQuestion` function that prompts the user with a question and captures their answer.
- **questions.js**: Exports a `getQuestions` function that reads questions from `questions.json` and parses them.

## Running the Project

To run the project, use the following command:

```sh
npm start
```

## Deployment

### Docker

A `Dockerfile` and `docker-compose.yml` are provided for containerized deployment.

1. **Build the Docker image**

   ```sh
   docker build -t quiz-game:1.0 .
   ```

2. **Run the Docker container**

   ```sh
   docker run --name quiz-game-container quiz-game:1.0
   ```

3. **Using Docker Compose**

   Alternatively, you can use Docker Compose to build and run the container.

   ```sh
   docker-compose up
   ```

## Development Workflow

### Setting Up

1. **Clone the repository**

   ```sh
   git clone <repository-url>
   cd quiz-game
   ```

2. **Install dependencies**

   ```sh
   npm install
   ```

### Making Changes

- Make your changes in a new branch and submit a pull request for review.
- Ensure that all tests pass before submitting a pull request.

### Testing

- Currently, there are no unit tests provided. You can manually test the application by running it and verifying the output.

## Additional Information

- This project uses the latest version of Node.js and its dependencies are managed via `npm`.
- Contributions are welcome. Please follow the standard GitHub workflow for submitting pull requests.
- For any questions or issues, please open an issue on the project's GitHub page.
