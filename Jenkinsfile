pipeline {
    agent none

    options {
        disableConcurrentBuilds()
        timeout(time: 90, unit: 'MINUTES')
        timestamps()
    }

    parameters {
        string(
            name: 'TENANT_ID',
            defaultValue: '',
            description: 'Run single tenant'
        )

        choice(
            name: 'ENVIRONMENT',
            choices: ['ALL', 'Ring 3a', 'Ring 3-aws', 'Ring 3b'],
            description: 'Environment filter'
        )

        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'Skip email sending'
        )
    }

    stages {
        stage('Turbo Email Automation') {
            agent {
                kubernetes {
                    label 'turbo-email-automation'
                    cloud 'kubernetes-kaniko-v2'
                    defaultContainer 'python-runner'
                    yaml """
apiVersion: v1
kind: Pod
spec:
  containers:
  - name: python-runner
    image: python:3.11-slim
    command:
    - cat
    tty: true
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "4Gi"
        cpu: "2000m"
"""
                }
            }

            stages {
                stage('Checkout') {
                    steps {
                        checkout scm
                    }
                }

                stage('Prepare Environment') {
                    steps {
                        container('python-runner') {
                            sh '''
                                apt-get update
                                apt-get install -y chromium chromium-driver

                                pip install --upgrade pip
                                pip install -r requirements.txt

                                cp .env.example .env
                            '''
                        }
                    }
                }

                stage('Run Automation') {
                    steps {
                        withCredentials([
                            usernamePassword(
                                credentialsId: 'Sendgrid_Key',
                                usernameVariable: 'userName',
                                passwordVariable: 'Sendgrid_Api_Key'
                            )
                        ]) {
                            container('python-runner') {
                                script {
                                    def cmd = 'python main.py'

                                    if (params.TENANT_ID?.trim()) {
                                        cmd += " --tenant ${params.TENANT_ID.trim()}"
                                    } else if (params.ENVIRONMENT != 'ALL') {
                                        cmd += ' --environment "' + params.ENVIRONMENT + '"'
                                    }

                                    if (params.DRY_RUN) {
                                        cmd += ' --dry-run'
                                    }

                                    sh """
                                        export \$(grep -v '^#' .env | xargs)
                                        export SENDGRID_API_KEY=${Sendgrid_Api_Key}

                                        ${cmd}
                                    """
                                }
                            }
                        }
                    }
                }

                stage('Archive Reports') {
                    steps {
                        archiveArtifacts artifacts: 'outputs/**', allowEmptyArchive: true
                    }
                }
            }
        }
    }
}