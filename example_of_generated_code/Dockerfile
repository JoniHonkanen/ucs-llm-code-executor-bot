# Use the official Node.js image as the base image
FROM node:alpine

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json if available
COPY package.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Command to run the application
CMD ["npm", "start"]