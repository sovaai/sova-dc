# SOVA DC

SOVA DC is a solution for distributed ASR and TTS computing based on [Kademlia](https://en.wikipedia.org/wiki/Kademlia), a distributed hash table for decentralized peer-to-peer networks. The network nodes are designed as REST API services that can be connected to [SOVA ASR](https://github.com/sovaai/sova-asr) and [SOVA TTS](https://github.com/sovaai/sova-tts) running locally. The list of nodes in a network that can provide ASR/TTS computing is constantly being refreshed in the background. It is only required to install Python 3.6+ with aiohttp and kademlia libraries to get ASR/TTS results from any device (even without ASR/TTS computing capacity). It is also required to know any network node IP address to connect to a network with computing capacities.

## Installation

If you want to provide your computing capacities to the network users or create your own distributed network first install Docker and docker-compose to create a node in a network. You also have to start SOVA ASR/SOVA TTS and open those services ports on the host machine.

#### Build and deploy network nodes

*   In order to run node in a distributed network you have to set your IP address with open ports for ASR/TTS services and (optionally) set neighbours you would like to connect to and share network requests with in `docker-compose.yml` run command section. For example set the following command if your IP address is 192.168.0.1 and you have SOVA ASR running on port 8888 and SOVA TTS running on port 8899 and you want to connect to a network your neighbour node 192.168.0.2 is connected to:
     ```bash
         command: bash -c "python3 client_dc.py --port 5678 --neighbours 192.168.0.2:5678 --services asr/cpu/192.168.0.1:8888,tts/gpu/192.168.0.1:8899"
     ```

*   Build docker image:
     ```bash
     $ sudo docker-compose build
     ```

*	Run docker container:
     ```bash
     $ sudo docker-compose up -d
     ```

#### Install pre-requisites to send ASR/TTS requests as a client:

*   First install Python 3.6+ and pip (brief instruction for Ubuntu). Install pre-requisites via pip:
     ```bash
     $ sudo apt-get install -y python3 python3-pip
     $ pip install -r requirements.txt
     ```

## Distributed runtime

*   To send ASR/TTS requests run `client_user.py` and IP address of any network node (node REST API services use port 5600 by default for client serving):

     ```bash
     $ python3 client_user.py --address 192.168.0.1:5600 --service asr --file Data/test.wav
     $ python3 client_user.py --address 192.168.0.1:5600 --service tts --text "Добрый день"
     ```
