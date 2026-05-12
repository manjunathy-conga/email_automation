pipeline {
    agent none

    options {
        disableConcurrentBuilds()
        timeout(time: 90, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        cron('TZ=Asia/Kolkata\n30 15 * * 1-5')
    }

    parameters {
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
                    defaultContainer 'python-builder'
                    yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    name: turbo-email-automation
spec:
  containers:
  - name: python-builder
    image: python:3.11
    imagePullPolicy: IfNotPresent
    command:
    - cat
    tty: true

  - name: ic-kaniko-builder
    image: congacicd.azurecr.io/ic-kaniko-builder:1.0.0
    imagePullPolicy: IfNotPresent
    command:
    - cat
    tty: true
    volumeMounts:
      - name: docker-config
        mountPath: /kaniko/.docker

  volumes:
  - name: docker-config
    projected:
      sources:
      - secret:
          name: devops-kaniko-secret
          items:
            - key: .dockerconfigjson
              path: config.json

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

                stage('Prepare Environment') {
                    steps {
                        container('python-builder') {
                            sh '''
                                set -x

                                apt-get update
                                apt-get install -y chromium chromium-driver wget curl unzip

                                python3 --version
                                pip3 --version

                                pip3 install --upgrade pip
                                pip3 install -r requirements.txt
                                pip3 install sendgrid
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
                            container('python-builder') {
                                sh """
                                    set -x

                                    export SENDGRID_API_KEY=${Sendgrid_Api_Key}

                                    export RING_3A_URL=https://ring3a-admin-grafana.congacloud.com
                                    export RING_3A_USER=ring3a
                                    export RING_3A_PASS=ring3a@123

                                    export RING_3_AWS_URL=https://ring3-aws-admin-grafana.congacloud.com
                                    export RING_3_AWS_USER=ring3-aws
                                    export RING_3_AWS_PASS=ring3-aws@123

                                    export RING_3B_URL=https://ring3b-admin-grafana.congacloud.com
                                    export RING_3B_USER=ring3b
                                    export RING_3B_PASS=ring3b@123

                                    export DASHBOARD_AUTH_TOKEN=

                                    export CHROME_BIN=/usr/bin/chromium
                                    export CHROMEDRIVER=/usr/bin/chromedriver

                                    ln -sf /usr/bin/chromium /usr/bin/google-chrome || true

                                    ${params.DRY_RUN ? 'python3 main.py --dry-run' : 'python3 main.py'}
                                """
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
