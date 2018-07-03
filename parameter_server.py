"""
Parameter server for distbelief
"""
import torch
import torch.distributed as dist
from torch.multiprocessing import Process
from utils import squash_model, send_message, init_processes, DEFAULT_LEARNING_RATE, MessageCode

from models.mnist import Net

import logging

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

_LOGGER = logging.getLogger(__name__)

class ParameterServer():

    def __init__(self, learning_rate, model, random_seed=42):
        """__init__

        :param learning_rate:
        :param params: a dict of str -> pytorch tensor that represents the gradients
        :param random_seed:
        """
        _LOGGER.info("Creating ParameterServer with LR: {}".format(learning_rate))
        self.learning_rate = learning_rate
        _LOGGER.info("Setting m_parameter")
        self.m_parameter = torch.zeros(squash_model(model).numel() + 1)
        self.parameter_shard = torch.rand(squash_model(model).numel())

    def receive(self, message_code, parameter):
        _LOGGER.info("Processing message: {}".format(message_code.name))

        if message_code == MessageCode.ParameterUpdate:
            #be sure to clone here
            self.parameter_shard = parameter.clone()

        elif message_code == MessageCode.ParameterRequest:
            send_message(MessageCode.ParameterUpdate, self.parameter_shard, dst=1)    

        elif message_code == MessageCode.GradientUpdate:
            self.parameter_shard -= self.learning_rate * parameter

    def run(self):
        _LOGGER.info("Parameter Server Running!")
        self.running = True
        while self.running:
            _LOGGER.info("Polling for data")
            dist.recv(tensor=self.m_parameter)
            _LOGGER.info("Got message")
            self.receive(MessageCode(self.m_parameter[0].item()), self.m_parameter[1:])

def init_server(rank, size):
    model = Net()
    server = ParameterServer(learning_rate=DEFAULT_LEARNING_RATE, model=model)
    server.run()

if __name__ == "__main__":
     p = Process(target = init_processes, args=(0, 2, init_server))
     p.start()
     p.join()
