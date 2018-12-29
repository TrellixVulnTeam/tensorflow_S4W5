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
                 model):

        self.checkpoints_to_keep = FLAGS.checkpoints_to_keep
        self.keep_checkpoint_every_n_hours = FLAGS.keep_checkpoint_every_n_hours
        self.max_steps = FLAGS.n_epoch
        self.save_checkpoint_steps = FLAGS.save_checkpoint_steps
        self.batch_size = FLAGS.batch_size
        self.message = message
        self.data = data
        self.global_step = tf.train.get_or_create_global_step()
        self.model = model

    def load(self):
        # Load Dataset
        dataset = self.data.load(self.data.x_train, self.data.y_train, batch_size=self.batch_size, is_training=True)
        self.iterator = dataset.make_initializable_iterator()
        inputs, labels = self.iterator.get_next()
        return inputs, labels

    def train(self):
        util = Utils()
        util.conf_log()

        #train
        inputs, corrects = self.load()
        logits = self.model.inference(inputs)
        train_loss = self.model.loss(logits, corrects)
        predict = self.model.predict(inputs)
        opt_op = self.model.optimize(train_loss, self.global_step)
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
        train_op = tf.group([opt_op] + update_ops)
        train_accuracy = self.model.evaluate(logits, corrects)

        #test
        test_inputs, test_labels = self.data.load_test(self.data.x_test, self.data.y_test)
        with tf.variable_scope(tf.get_variable_scope(), reuse=True):
            logits = self.model.inference(test_inputs)
        test_loss = self.model.loss(logits, test_labels)
        test_accuracy = self.model.evaluate(logits, test_labels)

        tf.summary.scalar('train/loss', train_loss)
        tf.summary.scalar('train/accuracy', train_accuracy)
        tf.summary.image('train/image', inputs)
        tf.summary.scalar('test/loss', test_loss)
        tf.summary.scalar('test/accuracy', test_accuracy)
        tf.summary.image('test/image', test_inputs)


        def init_fn(scaffold, session):
            session.run(self.iterator.initializer,feed_dict={self.data.features_placeholder: self.data.x_train,
                                                             self.data.labels_placeholder: self.data.y_train})

        # create saver
        scaffold = tf.train.Scaffold(
            init_fn=init_fn,
            saver=tf.train.Saver(
                max_to_keep=self.checkpoints_to_keep,
                keep_checkpoint_every_n_hours=self.keep_checkpoint_every_n_hours))

        tf.logging.set_verbosity(tf.logging.INFO)

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

        hooks = []
        hooks.append(MyLoggerHook(self.message, util.log_dir, metrics, every_n_iter=100))
        hooks.append(tf.train.NanTensorHook(train_loss))
        hooks.append(SavedModelBuilderHook(util.saved_model_path, signature_def_map))
        if self.max_steps:
            hooks.append(tf.train.StopAtStepHook(last_step=self.max_steps))
        
        session = tf.train.MonitoredTrainingSession(
            checkpoint_dir=util.model_path,
            hooks=hooks,
            scaffold=scaffold,
            save_checkpoint_steps=self.save_checkpoint_steps,
            summary_dir=util.tf_board)
        
        with session:
            while not session.should_stop():
                session.run([train_op])