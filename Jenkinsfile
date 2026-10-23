
pipeline {
    agent any

    environment {
        LOCAL_IMAGE = 'pdfmergersplitter:v1'
        DOCKER_IMAGE = 'tsamhitha26/pdfmergersplitter:v1'
    }

    stages {
        stage('Build Docker Image') {
            steps {
                bat 'docker build -t pdfmergersplitter:v1 .'
            }
        }

        stage('Docker Login') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_TOKEN'
                )]) {
                    bat 'echo %DOCKER_TOKEN% | docker login -u %DOCKER_USER% --password-stdin'
                }
            }
        }

        stage('Push Image to Docker Hub') {
            steps {
                bat 'docker tag %LOCAL_IMAGE% %DOCKER_IMAGE%'
                bat 'docker push %DOCKER_IMAGE%'
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                bat 'kubectl apply -f deployment.yaml'
                bat 'kubectl apply -f service.yaml'
            }
        }

        stage('Verify Deployment') {
            steps {
                bat 'kubectl rollout status deployment/pdfmergersplitter-deployment --timeout=180s'
                bat 'kubectl get pods'
                bat 'kubectl get services'
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed successfully!'
            echo 'Application URL: http://localhost:30089'
        }

        failure {
            echo 'Pipeline failed. Check Console Output for the error.'
        }

        always {
            bat 'docker logout'
        }
    }
}
