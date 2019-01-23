# -*- coding: utf-8 -*-
#tensorboard --logdir ./logs
import sys,os
sys.path.append(os.path.join(os.path.dirname(__file__), '../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../env'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../agents'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utility'))
import gym
import gym.spaces
import gym_ple
import numpy as np
import tensorflow as tf
from optimizer import *
from dqn import DQN,DDQN
from rl_trainer import Trainer
from cacher_env import CatcherObserver


def set_model(outdim):
    model_set = [['conv', 8, 32, 4, tf.nn.relu],
                 ['conv', 4, 64, 2, tf.nn.relu],
                 ['conv', 3, 64, 1, tf.nn.relu],
                 ['flat'],
                 ['fc', 256, tf.nn.relu],
                 ['fc', outdim, None]]
    return model_set


def main(argv):
    env = gym.make('Catcher-v0')
    env = CatcherObserver(env, 80, 80, 4)
    agent = eval(FLAGS.agent)(model=set_model(outdim=env.action_space.n),
                              n_actions=env.action_space.n,
                              n_features=env.observation_space.shape[0],
                              learning_rate=0.01,
                              batch_size=FLAGS.batch_size, 
                              e_greedy=0.9,
                              replace_target_iter=100,
                              e_greedy_increment=0.001,
                              optimizer=FLAGS.opt
                              )

    trainer = Trainer(agent=agent, 
                      env=env, 
                      n_episode=FLAGS.n_episode, 
                      max_step=FLAGS.step, 
                      replay_size=FLAGS.batch_size, 
                      data_size=10**6,
                      n_warmup=FLAGS.n_warmup,
                      priority=FLAGS.priority,
                      render=FLAGS.render)

    print()
    print("---Start Learning------")
    print("data : {}".format(env))
    print("Agent : {}".format(FLAGS.agent))
    print("epoch : {}".format(FLAGS.n_episode))
    print("step : {}".format(FLAGS.step))
    print("batch_size : {}".format(FLAGS.batch_size))
    print("learning rate : {}".format(FLAGS.lr))
    print("Optimizer : {}".format(FLAGS.opt))
    print("priority : {}".format(FLAGS.priority))
    print("n_warmup : {}".format(FLAGS.n_warmup))
    print("model_update : {}".format(FLAGS.model_update))
    print("-----------------------")
    trainer.train()


if __name__ == '__main__':
    flags = tf.app.flags
    FLAGS = flags.FLAGS
    flags.DEFINE_string('agent', 'DQN', 'Choise Agents -> [DQN, DDQN]')
    flags.DEFINE_integer('n_episode', '100000', 'Input max episode')
    flags.DEFINE_integer('step', '10000', 'Input max steps')
    flags.DEFINE_integer('batch_size', '32', 'Input batch size')
    flags.DEFINE_integer('n_warmup', '1000', 'n_warmup value')
    flags.DEFINE_integer('model_update', '1000', 'target_model_update_freq')
    flags.DEFINE_boolean('render', 'False', 'render')
    flags.DEFINE_boolean('priority', 'False', 'prioritized Experience Replay')
    flags.DEFINE_float('lr', '1e-4', 'Input learning rate')
    flags.DEFINE_string('opt','RMSProp','Choice the optimizer -> ["SGD","Momentum","Adadelta","Adagrad","Adam","RMSProp"]')
    tf.app.run()