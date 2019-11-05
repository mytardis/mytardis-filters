def stackName = 'test'
def serviceName = 'filters'
def workerLabel = "${serviceName}-${stackName}"
def dockerHubAccount = 'mytardis'
def dockerImageName = "k8s-${serviceName}"
def dockerImageTag = ''
def dockerImageFullNameTag = ''
def dockerImageFullNameLatest = "${dockerHubAccount}/${dockerImageName}:latest"
def k8sDeploymentNamespace = 'mytardis'

podTemplate(
    label: workerLabel,
    serviceAccount: 'jenkins',
    containers: [
        containerTemplate(
            name: 'docker',
            image: 'docker:19.03.2-dind',
            ttyEnabled: true,
            command: 'cat',
            envVars: [
                containerEnvVar(key: 'DOCKER_CONFIG', value: '/tmp/docker')
            ],
            resourceRequestCpu: '500m'
        ),
        containerTemplate(
            name: 'rabbitmq',
            image: 'rabbitmq:3.7',
            alwaysPullImage: false,
            envVars: [
                envVar(key: 'RABBITMQ_DEFAULT_USER', value: 'user'),
                envVar(key: 'RABBITMQ_DEFAULT_PASS', value: 'password')
            ]
        ),
        containerTemplate(
            name: 'memcached',
            image: 'memcached:1.5.12',
            alwaysPullImage: false
        ),
        containerTemplate(
            name: 'kubectl',
            image: 'lachlanevenson/k8s-kubectl:v1.15.4',
            ttyEnabled: true,
            command: 'cat',
            envVars: [
                containerEnvVar(key: 'KUBECONFIG', value: '/tmp/kube/admin.conf')
            ]
        )
    ],
    volumes: [
        secretVolume(secretName: "kube-config-${stackName}", mountPath: '/tmp/kube'),
        secretVolume(secretName: 'docker-config', mountPath: '/tmp/docker'),
        hostPathVolume(hostPath: '/var/run/docker.sock', mountPath: '/var/run/docker.sock')
    ]
) {
    node(workerLabel) {
        def ip = sh(returnStdout: true, script: 'hostname -i').trim()
        stage('Clone repository') {
            checkout scm
        }
        dockerImageTag = sh(returnStdout: true, script: 'git log -n 1 --pretty=format:"%h"').trim()
        dockerImageFullNameTag = "${dockerHubAccount}/${dockerImageName}:${dockerImageTag}"
        stage('Build image for tests') {
            container('docker') {
                sh("docker build . --tag ${dockerImageFullNameTag} --target=test")
            }
        }
        def dockerName = "${dockerImageName}-${dockerImageTag}"
        stage('Run test image as a service') {
            container('docker') {
                try {
                    sh("docker rm -f ${dockerName}")
                } catch(e) {}
                sh("docker run -d --rm --add-host rabbitmq:${ip} --add-host memcached:${ip} --name ${dockerName} ${dockerImageFullNameTag}")
            }
        }
        def tests = [:]
        [
            'pylint': "docker exec ${dockerName} pylint --rcfile .pylintrc ${serviceName}",
            'flake8': "docker exec ${dockerName} flake8 --config=.flake8 ${serviceName}",
            'pytest': "docker exec ${dockerName} pytest ${serviceName}"
        ].each { name, command ->
            tests[name] = {
                stage("Run test - ${name}") {
                    container('docker') {
                        sh(command)
                    }
                }
            }
        }
        parallel tests
        stage('Stop test image') {
            container('docker') {
                sh("docker stop ${dockerName}")
            }
        }
        stage('Build image for production') {
            container('docker') {
                sh("docker build . --tag ${dockerImageFullNameTag} --target=base")
            }
        }
        stage('Push image to DockerHub') {
            container('docker') {
                sh("docker push ${dockerImageFullNameTag}")
                sh("docker tag ${dockerImageFullNameTag} ${dockerImageFullNameLatest}")
                sh("docker push ${dockerImageFullNameLatest}")
            }
        }
        stage('Deploy image to Kubernetes') {
            container('kubectl') {
                sh ("kubectl -n ${k8sDeploymentNamespace} set image deployment/${serviceName} ${serviceName}=${dockerImageFullNameTag}")
            }
        }
    }
}
