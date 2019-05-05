import os,sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../../utility'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../network'))
import numpy as np
import tensorflow as tf
from agent import Agent
from eager_nn import EagerNN

class PolicyGradient(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def _build_net(self):
        # ------------------ build eval_net ------------------
        self.q_eval = eval(self.network)(model=self.model, out_dim=self.n_actions, name='Q_net', opt=self._optimizer, lr=self.lr, trainable=self.trainable, is_categorical=self.is_categorical)

    def inference(self, state):
        return tf.keras.layers.Softmax()(self.q_eval.inference(state))

    def choose_action(self, observation):
        observation = observation[np.newaxis, :]
        actions_value = self.inference(observation)
        action = np.random.choice(self.actions_list, size=1, p=np.array(actions_value).ravel())[0]
        return action

    def test_choose_action(self, observation):
        observation = observation[np.newaxis, :]
        actions_value = self.inference(observation)
        action = np.random.choice(self.actions_list, size=1, p=np.array(actions_value).ravel())[0]
        return action
        
    def update_q_net(self, replay_data, weights):
        self.bs, eval_act_index, done, bs_, reward, p_idx = replay_data

        # normalize rewards
        reward = self._discount_and_norm_rewards(reward)

        global_step = tf.train.get_or_create_global_step()

        with tf.GradientTape() as tape:
            one_hot_actions = tf.one_hot(eval_act_index, depth=self.n_actions)
            q_eval = self.inference(self.bs)
            selected_action_probs = tf.reduce_sum(q_eval * one_hot_actions, axis=1)
            clipped = tf.clip_by_value(selected_action_probs, 1e-10, 1.0)
            self.td_error = -tf.log(clipped) * reward
            self.loss = tf.reduce_mean(self.td_error * weights)
        self.q_eval.optimize(self.loss, global_step, tape)

        #sys.exit()
        
        return