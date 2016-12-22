import numpy as np
from keras import backend as K
from Tools.preprocessor import prep_run
import Tools.inputiterator as ii
import keras.callbacks
from itertools import cycle


def pad_label_with_blank(label, blank_id, max_length):
    """

    :param label:
    :param blank_id:
    :param max_length:
    :return:
    """
    label_len_1 = len(label[0])
    label_len_2 = len(label[0])

    label_pad = []
    # label_pad.append(blank_id)
    for _ in label[0]:
        label_pad.append(_)
        # label_pad.append(blank_id)

    while label_len_2 < max_length:
        label_pad.append(-1)
        label_len_2 += 1

    label_out = np.ones(shape=[max_length]) * np.asarray(blank_id)

    trunc = label_pad[:max_length]
    label_out[:len(trunc)] = trunc

    return label_out, label_len_1


class InputGenerator(keras.callbacks.Callback):
    def __init__(self, minibatch_size, img_w, img_h, downsample_width, output_size, absolute_max_string_len):
        self.minibatch_size = minibatch_size
        self.img_w = img_w
        self.img_h = img_h
        self.downsample_width = downsample_width
        self.output_size = output_size
        self.absolute_max_string_len = absolute_max_string_len

        self.cur_train_index = 0
        self.data_train = []
        self.data_test = []

        # load the IAM Dataset
        self.data_train = cycle(ii.input_iter_run_train(self.minibatch_size))
        self.data_test = cycle(ii.input_iter_run_test(self.minibatch_size))

    def get_batch(self, size, train):
        batch_size = size
        #######################
        # 1. InputIterator Zeug
        if train:
            input_iterator = self.data_train.__next__()[0]  # get from train data
        else:
            input_iterator = self.data_test.__next__()[0]  # get from test data

        #######################
        # 2. Preprocessor
        preprocessed_input = prep_run(input_iterator, 0)
        # Output = [img_noise, label_blank, label_len, label_raw]

        #######################
        # 3. Predictor Zeug
        # Define input shapes
        # 1 Image
        # 2 Label with blanks
        # 3 Input length
        # 4 Label Length
        # 5 True label

        if K.image_dim_ordering() == 'th':
            in1 = np.ones([batch_size, 1, self.img_h, self.img_w])
        else:
            in1 = np.ones([batch_size, self.img_h, self.img_w, 1])
        in2 = np.ones([batch_size, self.absolute_max_string_len])
        in3 = np.zeros([batch_size, 1])
        in4 = np.zeros([batch_size, 1])
        in5 = []

        # Define dummy output shape
        out1 = np.zeros([batch_size])

        # Pad/Cut all input to network size
        for idx, inp in enumerate(preprocessed_input):
            x_padded = inp[0]
            y_with_blank = inp[1]
            y_len = inp[2]

            # Prepare input for model
            if K.image_dim_ordering() == 'th':
                in1[idx, 0, :, :] = np.asarray(x_padded, dtype='float32')[:, :]
            else:
                in1[idx, :, :, 0] = np.asarray(x_padded, dtype='float32')[:, :]
            in2[idx, :] = np.asarray(y_with_blank, dtype='float32')
            in3[idx, :] = np.array([self.downsample_width], dtype='float32')
            in4[idx, :] = np.array([y_len], dtype='float32')
            in5.append(inp[3])

        # Dictionary for Keras Model Input
        inputs = {'the_input': in1,
                  'the_labels': in2,
                  'input_length': in3,
                  'label_length': in4,
                  'source_str': in5  # used for report only
                  }
        outputs = {'ctc': out1}
        return inputs, outputs

    def next_train(self):
        while 1:
            ret = self.get_batch(self.minibatch_size, train=True)
            yield ret

    def next_val(self):
        while 1:
            ret = self.get_batch(self.minibatch_size, train=False)
            yield ret
