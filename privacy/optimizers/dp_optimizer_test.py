# Copyright 2018, The TensorFlow Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for differentially private optimizers."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from absl.testing import parameterized
import mock
import numpy as np
import tensorflow as tf

from privacy.optimizers import dp_optimizer


def loss(val0, val1):
  """Loss function that is minimized at the mean of the input points."""
  return 0.5 * tf.reduce_sum(tf.squared_difference(val0, val1), axis=1)


class DPOptimizerTest(tf.test.TestCase, parameterized.TestCase):

  # Parameters for testing: optimizer, num_microbatches, expected answer.
  @parameterized.named_parameters(
      ('DPGradientDescent 1', dp_optimizer.DPGradientDescentOptimizer, 1,
       [-10.0, -10.0]),
      ('DPGradientDescent 2', dp_optimizer.DPGradientDescentOptimizer, 2,
       [-5.0, -5.0]),
      ('DPGradientDescent 4', dp_optimizer.DPGradientDescentOptimizer, 4,
       [-2.5, -2.5]),
      ('DPAdagrad 1', dp_optimizer.DPAdagradOptimizer, 1, [-10.0, -10.0]),
      ('DPAdagrad 2', dp_optimizer.DPAdagradOptimizer, 2, [-5.0, -5.0]),
      ('DPAdagrad 4', dp_optimizer.DPAdagradOptimizer, 4, [-2.5, -2.5]),
      ('DPAdam 1', dp_optimizer.DPAdamOptimizer, 1, [-10.0, -10.0]),
      ('DPAdam 2', dp_optimizer.DPAdamOptimizer, 2, [-5.0, -5.0]),
      ('DPAdam 4', dp_optimizer.DPAdamOptimizer, 4, [-2.5, -2.5]))
  def testBaseline(self, cls, num_microbatches, expected_answer):
    with self.cached_session() as sess:
      var0 = tf.Variable([1.0, 2.0])
      data0 = tf.Variable([[3.0, 4.0], [5.0, 6.0], [7.0, 8.0], [-1.0, 0.0]])

      opt = cls(
          l2_norm_clip=1.0e9,
          noise_multiplier=0.0,
          num_microbatches=num_microbatches,
          learning_rate=2.0)

      self.evaluate(tf.global_variables_initializer())
      # Fetch params to validate initial values
      self.assertAllClose([1.0, 2.0], self.evaluate(var0))

      # Expected gradient is sum of differences divided by number of
      # microbatches.
      gradient_op = opt.compute_gradients(loss(data0, var0), [var0])
      grads_and_vars = sess.run(gradient_op)
      self.assertAllCloseAccordingToType(expected_answer, grads_and_vars[0][0])

  @parameterized.named_parameters(
      ('DPGradientDescent', dp_optimizer.DPGradientDescentOptimizer),
      ('DPAdagrad', dp_optimizer.DPAdagradOptimizer),
      ('DPAdam', dp_optimizer.DPAdamOptimizer))
  def testClippingNorm(self, cls):
    with self.cached_session() as sess:
      var0 = tf.Variable([0.0, 0.0])
      data0 = tf.Variable([[3.0, 4.0], [6.0, 8.0]])

      opt = cls(
          l2_norm_clip=1.0,
          noise_multiplier=0.0,
          num_microbatches=1,
          learning_rate=2.0)

      self.evaluate(tf.global_variables_initializer())
      # Fetch params to validate initial values
      self.assertAllClose([0.0, 0.0], self.evaluate(var0))

      # Expected gradient is sum of differences.
      gradient_op = opt.compute_gradients(loss(data0, var0), [var0])
      grads_and_vars = sess.run(gradient_op)
      self.assertAllCloseAccordingToType([-0.6, -0.8], grads_and_vars[0][0])

  @parameterized.named_parameters(
      ('DPGradientDescent', dp_optimizer.DPGradientDescentOptimizer),
      ('DPAdagrad', dp_optimizer.DPAdagradOptimizer),
      ('DPAdam', dp_optimizer.DPAdamOptimizer))
  def testNoiseMultiplier(self, cls):
    with self.cached_session() as sess:
      var0 = tf.Variable([0.0])
      data0 = tf.Variable([[0.0]])

      opt = cls(
          l2_norm_clip=4.0,
          noise_multiplier=2.0,
          num_microbatches=1,
          learning_rate=2.0)

      self.evaluate(tf.global_variables_initializer())
      # Fetch params to validate initial values
      self.assertAllClose([0.0], self.evaluate(var0))

      gradient_op = opt.compute_gradients(loss(data0, var0), [var0])
      grads = []
      for _ in xrange(1000):
        grads_and_vars = sess.run(gradient_op)
        grads.append(grads_and_vars[0][0])

      # Test standard deviation is close to l2_norm_clip * noise_multiplier.
      self.assertNear(np.std(grads), 2.0 * 4.0, 0.5)

  @mock.patch.object(tf, 'logging')
  def testComputeGradientsOverrideWarning(self, mock_logging):

    class SimpleOptimizer(tf.train.Optimizer):

      def compute_gradients(self):
        return 0

    dp_optimizer.make_optimizer_class(SimpleOptimizer)
    mock_logging.warning.assert_called_once_with(
        'WARNING: Calling make_optimizer_class() on class %s that overrides '
        'method compute_gradients(). Check to ensure that '
        'make_optimizer_class() does not interfere with overridden version.',
        'SimpleOptimizer')

if __name__ == '__main__':
  tf.test.main()
