import os
import numpy as np
import cv2
import tensorflow._api.v2.compat.v1 as tf
tf.compat.v1.disable_v2_behavior()
from sklearn.model_selection import train_test_split


class PlateCNN:
    def __init__(self):
        self.img_w, self.img_h = 136, 36
        self.y_size = 2
        self.batch_size = 100
        self.learn_rate = 0.001

        self.x_place = tf.placeholder(dtype=tf.float32, shape=[None, self.img_h, self.img_w, 3], name='x_place')
        self.y_place = tf.placeholder(dtype=tf.float32, shape=[None, self.y_size], name='y_place')
        self.keep_place = tf.placeholder(dtype=tf.float32, name='keep_place')

    def cnn_construct(self):
        x_input = tf.reshape(self.x_place, shape=[-1, self.img_h, self.img_w, 3])

        cw1 = tf.Variable(tf.random_normal(shape=[3, 3, 3, 32], stddev=0.01), dtype=tf.float32)
        cb1 = tf.Variable(tf.random_normal(shape=[32]), dtype=tf.float32)
        conv1 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(x_input, filter=cw1, strides=[1, 1, 1, 1], padding='SAME'), cb1))
        conv1 = tf.nn.max_pool(conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
        conv1 = tf.nn.dropout(conv1, self.keep_place)

        cw2 = tf.Variable(tf.random_normal(shape=[3, 3, 32, 64], stddev=0.01), dtype=tf.float32)
        cb2 = tf.Variable(tf.random_normal(shape=[64]), dtype=tf.float32)
        conv2 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(conv1, filter=cw2, strides=[1, 1, 1, 1], padding='SAME'), cb2))
        conv2 = tf.nn.max_pool(conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
        conv2 = tf.nn.dropout(conv2, self.keep_place)

        cw3 = tf.Variable(tf.random_normal(shape=[3, 3, 64, 128], stddev=0.01), dtype=tf.float32)
        cb3 = tf.Variable(tf.random_normal(shape=[128]), dtype=tf.float32)
        conv3 = tf.nn.relu(tf.nn.bias_add(tf.nn.conv2d(conv2, filter=cw3, strides=[1, 1, 1, 1], padding='SAME'), cb3))
        conv3 = tf.nn.max_pool(conv3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
        conv3 = tf.nn.dropout(conv3, self.keep_place)

        conv_out = tf.reshape(conv3, shape=[-1, 17 * 5 * 128])

        fw1 = tf.Variable(tf.random_normal(shape=[17 * 5 * 128, 1024], stddev=0.01), dtype=tf.float32)
        fb1 = tf.Variable(tf.random_normal(shape=[1024]), dtype=tf.float32)
        fully1 = tf.nn.relu(tf.add(tf.matmul(conv_out, fw1), fb1))
        fully1 = tf.nn.dropout(fully1, self.keep_place)

        fw2 = tf.Variable(tf.random_normal(shape=[1024, 1024], stddev=0.01), dtype=tf.float32)
        fb2 = tf.Variable(tf.random_normal(shape=[1024]), dtype=tf.float32)
        fully2 = tf.nn.relu(tf.add(tf.matmul(fully1, fw2), fb2))
        fully2 = tf.nn.dropout(fully2, self.keep_place)

        fw3 = tf.Variable(tf.random_normal(shape=[1024, self.y_size], stddev=0.01), dtype=tf.float32)
        fb3 = tf.Variable(tf.random_normal(shape=[self.y_size]), dtype=tf.float32)
        fully3 = tf.add(tf.matmul(fully2, fw3), fb3, name='out_put')

        return fully3

    def train(self, train_data_dir, model_save_path):
        print('ready load train dataset')
        x, y = self.init_data(train_data_dir)
        print('success load ' + str(len(y)) + ' datas')
        train_x, test_x, train_y, test_y = train_test_split(x, y, test_size=0.2, random_state=0)

        out_put = self.cnn_construct()
        predicts = tf.nn.softmax(out_put)
        predicts = tf.argmax(predicts, axis=1)
        actual_y = tf.argmax(self.y_place, axis=1)
        accuracy = tf.reduce_mean(tf.cast(tf.equal(predicts, actual_y), dtype=tf.float32))
        cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=out_put, labels=self.y_place))
        opt = tf.train.AdamOptimizer(self.learn_rate)
        train_step = opt.minimize(cost)

        with tf.Session() as sess:
            init = tf.global_variables_initializer()
            sess.run(init)
            step = 0
            saver = tf.train.Saver()
            while True:
                train_index = np.random.choice(len(train_x), self.batch_size, replace=False)
                train_randx = train_x[train_index]
                train_randy = train_y[train_index]
                _, loss = sess.run([train_step, cost], feed_dict={self.x_place: train_randx,
                                                                  self.y_place: train_randy, self.keep_place: 0.75})
                step += 1
                print(step, loss)

                if step % 10 == 0:
                    test_index = np.random.choice(len(test_x), self.batch_size, replace=False)
                    test_randx = test_x[test_index]
                    test_randy = test_y[test_index]
                    acc = sess.run(accuracy, feed_dict={self.x_place: test_randx,
                                                        self.y_place: test_randy, self.keep_place: 1.0})
                    print('accuracy:' + str(acc))
                    if acc > 0.99 and step > 500:
                        saver.save(sess, model_save_path, global_step=step)
                        break

    def test(self, x_images, test_model_path):
        out_put = self.cnn_construct()
        predicts = tf.nn.softmax(out_put)
        probabilitys = tf.reduce_max(predicts, reduction_indices=[1])
        predicts = tf.argmax(predicts, axis=1)
        saver = tf.train.Saver()
        with tf.Session() as sess:
            sess.run(tf.global_variables_initializer())
            saver.restore(sess, test_model_path)
            pred_res, prob_res = sess.run([predicts, probabilitys],
                                          feed_dict={self.x_place: x_images, self.keep_place: 1.0})
        return pred_res, prob_res

    def list_all_files(self, root):
        files = []
        list_all = os.listdir(root)
        for num in range(len(list_all)):
            element = os.path.join(root, list_all[num])
            if os.path.isdir(element):
                files.extend(self.list_all_files(element))
            elif os.path.isfile(element):
                files.append(element)
        return files

    def init_data(self, init_dir):
        x = []
        y = []
        if not os.path.exists(init_dir):
            raise ValueError('没有找到文件夹')
        files = self.list_all_files(init_dir)
        labels = [os.path.split(os.path.dirname(file))[-1] for file in files]

        for num, file in enumerate(files):
            src_img = cv2.imread(file)
            if src_img.ndim != 3:
                continue
            resize_img = cv2.resize(src_img, (136, 36))
            x.append(resize_img)
            y.append([[0, 1] if labels[num] == 'has' else [1, 0]])

        x = np.array(x)
        y = np.array(y).reshape(-1, 2)
        return x, y

    def init_test_data(self, test_data_dir):
        test_x = []
        if not os.path.exists(test_data_dir):
            raise ValueError('没有找到文件夹')
        files = self.list_all_files(test_data_dir)
        for file in files:
            src_img = cv2.imread(file, cv2.COLOR_BGR2GRAY)
            if src_img.ndim != 3:
                continue
            resize_img = cv2.resize(src_img, (136, 36))
            test_x.append(resize_img)
        test_x = np.array(test_x)
        return test_x


if __name__ == '__main__':
    data_dir = os.path.join('./cv-cnn-lpr-main/data/train/cnn_plate_train')
    test_dir = os.path.join('./cv-cnn-lpr-main/data/train/cnn_plate_test')
    train_model_path = os.path.join('./cv-cnn-lpr-main/data/model/plate_recognize/model.ckpt')
    model_path = os.path.join('./cv-cnn-lpr-main/data/model/plate_recognize/model.ckpt-510')

    train_flag = 0
    # train_flag = 1 ：训练模型
    # train_flag = 0 ：测试模型的准确度
    net = PlateCNN()

    if train_flag == 1:
        # 训练模型
        net.train(data_dir, train_model_path)
    else:
        # 测试部分
        test_X = net.init_test_data(test_dir)
        preds, probs = net.test(test_X, model_path)
        for i in range(len(preds)):
            pred = preds[i].astype(int)
            prob = probs[i]
            if pred == 1:
                print('plate', prob)
            else:
                print('no', prob)
