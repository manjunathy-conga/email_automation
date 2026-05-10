pipeline {
    agent none

    options {
        disableConcurrentBuilds()
        timeout(time: 90, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timestamps()
    }

    parameters {
        string(
            name: 'TENANT_ID',
            defaultValue: '',
            description: 'Run a single tenant (example: ibm). Leave blank for all tenants.'
        )

        choice(
            name: 'ENVIRONMENT',
            choices: ['ALL', 'Ring 3a', 'Ring 3-aws', 'Ring 3b'],
            description: 'Environment filter'
        )

        booleanParam(
            name: 'DRY_RUN',
            defaultValue: false,
            description: 'Generate reports only. Skip email.'
        )
    }

    environment {
        SENDGRID_API_KEY = credentials('SENDGRID_API_KEY')

        RING_3A_URL     = credentials('RING_3A_URL')
        RING_3A_USER    = credentials('RING_3A_USER')
        RING_3A_PASS    = credentials('RING_3A_PASS')

        RING_3_AWS_URL  = credentials('RING_3_AWS_URL')
        RING_3_AWS_USER = credentials('RING_3_AWS_USER')
        RING_3_AWS_PASS = credentials('RING_3_AWS_PASS')

        RING_3B_URL     = credentials('RING_3B_URL')
        RING_3B_USER    = credentials('RING_3B_USER')
        RING_3B_PASS    = credentials('RING_3B_PASS')
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
metadata:
  labels:
    app: turbo-email-automation
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

  imagePullSecrets:
  - name: devops-kaniko-secret
"""
                }
            }

            stages {
                stage('Checkout') {
                    steps {
                        checkout scm
                    }
                }

                stage('Install Dependencies') {
                    steps {
                        container('python-runner') {
                            sh '''
                                apt-get update -qq
                                apt-get install -y \
                                    chromium \
                                    chromium-driver \
                                    wget \
                                    curl \
                                    unzip \
                                    ca-certificates

                                pip install --upgrade pip
                                pip install -r requirements.txt
                            '''
                        }
                    }
                }

                stage('Run Automation') {
                    steps {
                        container('python-runner') {
                            script {
                                def cmd = "python main.py"

                                if (params.TENANT_ID?.trim()) {
                                    cmd += " --tenant ${params.TENANT_ID.trim()}"
                                } else if (params.ENVIRONMENT != 'ALL') {
                                    cmd += " --environment \\"${params.ENVIRONMENT}\\""
                                }

                                if (params.DRY_RUN) {
                                    cmd += " --dry-run"
                                }

                                withEnv([
                                    "SENDGRID_API_KEY=${env.SENDGRID_API_KEY}",

                                    "RING_3A_URL=${env.RING_3A_URL}",
                                    "RING_3A_USER=${env.RING_3A_USER}",
                                    "RING_3A_PASS=${env.RING_3A_PASS}",

                                    "RING_3_AWS_URL=${env.RING_3_AWS_URL}",
                                    "RING_3_AWS_USER=${env.RING_3_AWS_USER}",
                                    "RING_3_AWS_PASS=${env.RING_3_AWS_PASS}",

                                    "RING_3B_URL=${env.RING_3B_URL}",
                                    "RING_3B_USER=${env.RING_3B_USER}",
                                    "RING_3B_PASS=${env.RING_3B_PASS}",

                                    "CHROMIUM_PATH=/usr/bin/chromium",
                                    "CHROMEDRIVER_PATH=/usr/bin/chromedriver"
                                ]) {
                                    sh cmd
                                }
                            }
                        }
                    }
                }

                stage('Archive Reports') {
                    steps {
                        archiveArtifacts artifacts: 'outputs/reports/**', allowEmptyArchive: true
                        archiveArtifacts artifacts: 'outputs/*.log', allowEmptyArchive: true
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Turbo email automation completed successfully'
        }

        failure {
            mail(
                to: 'manjunathy@conga.com',
                subject: "Turbo Email Automation FAILED - ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: """
Job failed.

Job Name: ${env.JOB_NAME}
Build Number: ${env.BUILD_NUMBER}
Build URL: ${env.BUILD_URL}
"""
            )
        }

        always {
            cleanWs()
        }
    }
}