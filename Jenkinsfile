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
                    defaultContainer 'jnlp'
                    yaml """
apiVersion: v1
kind: Pod
metadata:
  labels:
    name: turbo-email-automation
spec:
  containers:
  - name: ic-utility-builder
    image: congacicd.azurecr.io/ic-utility-builder:1.1.1
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
                        container('ic-utility-builder') {
                            sh '''
                                set -x

                                pwd
                                ls -la

                                python3 --version
                                pip3 --version

                                pip3 install --upgrade pip
                                pip3 install -r requirements.txt
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
                            container('ic-utility-builder') {
                                script {
                                    def cmd = 'python3 main.py'

                                    if (params.TENANT_ID?.trim()) {
                                        cmd += " --tenant ${params.TENANT_ID.trim()}"
                                    } else if (params.ENVIRONMENT != 'ALL') {
                                        cmd += ' --environment "' + params.ENVIRONMENT + '"'
                                    }

                                    if (params.DRY_RUN) {
                                        cmd += ' --dry-run'
                                    }

                                    sh """
                                        set -x
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