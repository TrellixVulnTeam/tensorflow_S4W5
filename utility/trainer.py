import sys
sys.path.append('./utility')
sys.path.append('./network')
sys.path.append('./dataset')
import tensorflow as tf
from utils import Utils
from collections import OrderedDict
from hooks import SavedModelBuilderHook, MyLoggerHook

class Train():
    def __init__(self,
                 FLAGS,
                 message,
                 data,
                 model,
                 name):

        self.checkpoints_to_keep = FLAGS.checkpoints_to_keep
        self.keep_checkpoint_every_n_hours = FLAGS.keep_checkpoint_every_n_hours
        self.max_steps = FLAGS.n_epoch
        self.save_checkpoint_steps = FLAGS.save_checkpoint_steps
        self.batch_size = FLAGS.batch_size
        self.name = name
        self.message = message
        self.data = data
        self.global_step = tf.train.get_or_create_global_step()
        self.model = model

    def load(self):
        # Load Dataset
        dataset = self.data.load(self.data.x_train, self.data.y_train, batch_size=self.batch_size, is_training=True)
        valid = self.data.load(self.data.x_test, self.data.y_test, batch_size=self.batch_size*3, is_training=True)
        self.iterator = dataset.make_initializable_iterator()
        self.valid_iter = valid.make_initializable_iterator()
        inputs, labels = self.iterator.get_next()
        valid_inputs, valid_labels = self.valid_iter.get_next()
        return inputs, labels, valid_inputs, valid_labels

    def train(self):
        
        #train
        inputs, corrects, valid_inputs, valid_labels = self.load()
        logits = self.model.inference(inputs)
        train_loss = self.model.loss(logits, corrects)
        predict = self.model.predict(inputs)
        opt_op = self.model.optimize(train_loss, self.global_step)
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        train_op = tf.group([opt_op] + update_ops)
        train_accuracy = self.model.evaluate(logits, corrects)

        #test
        logits = self.model.inference(valid_inputs, reuse=True)
        test_loss = self.model.loss(logits, valid_labels)
        test_accuracy = self.model.evaluate(logits, valid_labels)

        tf.summary.scalar('train/loss', train_loss)
        tf.summary.scalar('train/accuracy', train_accuracy)
        tf.summary.image('train/image', inputs)
        tf.summary.scalar('test/loss', test_loss)
        tf.summary.scalar('test/accuracy', test_accuracy)
        tf.summary.image('test/image', valid_inputs)
        if self.name == 'AutoEncoder':
            tf.summary.image('test/encode_image', logits)


        def init_fn(scaffold, session):
            session.run([self.iterator.initializer,self.valid_iter.initializer],
                        feed_dict={self.data.features_placeholder: self.data.x_train,
                                   self.data.labels_placeholder: self.data.y_train,
                                   self.data.valid_placeholder: self.data.x_test,
                                   self.data.valid_labels_placeholder: self.data.y_test})

        # create saver
        scaffold = tf.train.Scaffold(
            init_fn=init_fn,
            saver=tf.train.Saver(
                max_to_keep=self.checkpoints_to_keep,
                keep_checkpoint_every_n_hours=self.keep_checkpoint_every_n_hours))

        tf.logging.set_verbosity(tf.logging.INFO)
        config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)

        signature_def_map = {
                        'predict': tf.saved_model.signature_def_utils.build_signature_def(
                            inputs={'inputs': tf.saved_model.utils.build_tensor_info(self.data.features_placeholder)},
                            outputs={'predict':  tf.saved_model.utils.build_tensor_info(predict)},
                            method_name=tf.saved_model.signature_constants.PREDICT_METHOD_NAME,)
                        }

        metrics = OrderedDict({
            "global_step": self.global_step,
            "train loss": train_loss,
            "train accuracy":train_accuracy,
            "test loss": test_loss,
            "test accuracy":test_accuracy})

        if self.name == 'tuning':
            hooks = []
            hooks.append(tf.train.LoggingTensorHook(metrics, every_n_iter=100))
            hooks.append(tf.train.NanTensorHook(train_loss))
            if self.max_steps:
                hooks.append(tf.train.StopAtStepHook(last_step=self.max_steps))

            # training
            session = tf.train.MonitoredTrainingSession(
                config=config,
                hooks=hooks,
                scaffold=scaffold)

        else:

            util = Utils(prefix=self.name)
            util.conf_log()

            hooks = []
            hooks.append(MyLoggerHook(self.message, util.log_dir, metrics, every_n_iter=100))
            hooks.append(tf.train.NanTensorHook(train_loss))
            hooks.append(SavedModelBuilderHook(util.saved_model_path, signature_def_map))
            if self.max_steps:
                hooks.append(tf.train.StopAtStepHook(last_step=self.max_steps))
            
            session = tf.train.MonitoredTrainingSession(
                config=config,
                checkpoint_dir=util.model_path,
                hooks=hooks,
                scaffold=scaffold,
                save_checkpoint_steps=self.save_checkpoint_steps,
                summary_dir=util.tf_board)
        
        with session:
            while not session.should_stop():
                _, loss, train_acc, test_acc = session.run([train_op, train_loss, train_accuracy, test_accuracy])
            
        return loss, train_acc, test_acc