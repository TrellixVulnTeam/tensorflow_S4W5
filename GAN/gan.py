import os,sys
sys.path.append('./network')
sys.path.append('./utility')
import tensorflow as tf
import math
from cnn import CNN
from optimizer import *
from generator import Generator
from discriminator import Discriminator


class GAN(CNN):
    def __init__(self,
                 z_dim=100,
                 name='GAN',
                 opt=Adam,
                 lr=0.001,
                 trainable=False,
                 interval=2):
        super().__init__(name=name, opt=opt, lr=lr, trainable=trainable)
        gen_model, dis_model = self.build()
        self.generator = Generator(model=gen_model, opt=opt, trainable=trainable)
        self.discriminator = Discriminator(model=dis_model, opt=opt, trainable=trainable)
        self.gen_train_interval = interval
        self.eps = 1e-14
        self._z_dim = z_dim

    def conv_out_size_same(self, size, stride):
        return int(math.ceil(float(size) / float(stride)))

    def build(self):
        s_h = 28
        s_h2 = self.conv_out_size_same(s_h, 2)
        s_h4 = self.conv_out_size_same(s_h2, 2)
        s_h8 = self.conv_out_size_same(s_h4, 2)
        s_h16 = self.conv_out_size_same(s_h8, 2)

        gen_model = [['fc', 512*s_h16*s_h16, None],
                     ['reshape', [-1, s_h16, s_h16, 512]],
                     ['BN'],
                     ['ReLU'],
                     ['deconv', s_h8, 256, 2, None],
                     ['BN'],
                     ['ReLU'],
                     ['deconv', s_h4, 128, 2, None],
                     ['BN'],
                     ['ReLU'],
                     ['deconv', s_h2, 64, 2, None],
                     ['BN'],
                     ['ReLU'],
                     ['deconv', s_h, 1, 2, None],
                     ['tanh']]


        dis_model = [['conv', 5, 64, 2, tf.nn.leaky_relu],
                     ['conv', 5, 128, 2, None],
                     ['BN'],
                     ['Leaky_ReLU'],
                     ['conv', 5, 256, 2, None],
                     ['BN'],
                     ['Leaky_ReLU'],
                     ['conv', 5, 512, 2, None],
                     ['BN'],
                     ['Leaky_ReLU'],
                     ['fc', 1, None]
                     ]

        return gen_model, dis_model

    def inference(self, inputs, batch_size):
        with tf.variable_scope(self.name):
            z = tf.random_normal((batch_size, self._z_dim), dtype=tf.float32)
            self.z = tf.reshape(z, [batch_size, 1, 1, self._z_dim])
            self.G = self.generator.inference(self.z)
            
            self.D, self.D_logits = self.discriminator.inference(inputs)               # input Correct data
            self.D_, self.D_logits_ = self.discriminator.inference(self.G, reuse=True) # input Fake data

            return self.D, self.D_logits, self.D_, self.D_logits_, self.G

    def predict(self):
        return self.generator.inference(self.z)

    def loss(self, img, fake_img):
        d_loss = - (tf.reduce_mean(tf.log(img + self.eps)) + tf.reduce_mean(tf.log(1 - fake_img + self.eps)))
        g_loss = - tf.reduce_mean(tf.log(fake_img + self.eps))

        return d_loss, g_loss

    def optimize(self, dis_loss, gen_loss):
        global_steps = tf.train.get_or_create_global_step()
        with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
            return self.generator.optimize(loss=gen_loss, global_step=global_steps), self.discriminator.optimize(loss=dis_loss, global_step=global_steps)
        
        
    