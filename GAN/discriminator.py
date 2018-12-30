import os,sys
sys.path.append('./network')
sys.path.append('./utility')
import tensorflow as tf
from model import CNN
from optimizer import *

class Discriminator(CNN):
    def __init__(self, 
                 model,
                 opt=Adam,
                 name='Discriminator',
                 trainable=False):
        super().__init__(model=model, name=name, opt=opt, trainable=trainable)

    def inference(self, outputs):
        with tf.variable_scope(self.name):
            for l in range(len(self.model)):
                outputs = (eval('self.' + self.model[l][0])(outputs, self.model[l][1:]))
            outputs  = tf.identity(outputs, name="output_logits")
            return outputs