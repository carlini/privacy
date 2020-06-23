# Copyright 2020, The TensorFlow Authors.
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

# Lint as: python3
"""Tests for tensorflow_privacy.privacy.membership_inference_attack.utils."""
from absl.testing import absltest

import numpy as np

from tensorflow_privacy.privacy.membership_inference_attack import utils


class UtilsTest(absltest.TestCase):

  def __init__(self, methodname):
    """Initialize the test class."""
    super().__init__(methodname)
    rng = np.random.RandomState(33)
    logits = rng.uniform(low=0, high=1, size=(1000, 14))
    loss = rng.uniform(low=0, high=1, size=(1000,))
    is_train = rng.binomial(1, 0.7, size=(1000,))
    self.mydict = {'logits': logits, 'loss': loss, 'is_train': is_train}

  def test_compute_metrics(self):
    """Test computation of attack metrics."""
    true = np.array([0, 0, 0, 1, 1, 1])
    pred = np.array([0.6, 0.9, 0.4, 0.8, 0.7, 0.2])

    results = utils.compute_performance_metrics(true, pred, threshold=0.5)

    for k in ['precision', 'recall', 'accuracy', 'f1_score', 'fpr', 'tpr',
              'thresholds', 'auc', 'advantage']:
      self.assertIn(k, results)

    np.testing.assert_almost_equal(results['accuracy'], 1. / 2.)
    np.testing.assert_almost_equal(results['precision'], 2. / (2. + 2.))
    np.testing.assert_almost_equal(results['recall'], 2. / (2. + 1.))

  def test_prepend_to_keys(self):
    """Test prepending of text to keys of a dictionary."""
    mydict = utils.prepend_to_keys(self.mydict, 'test')
    for k in mydict:
      self.assertTrue(k.startswith('test'))

  def test_select_indices(self):
    """Test selecting indices from dictionary with array values."""
    mydict = {'a': np.arange(10), 'b': np.linspace(0, 1, 10)}

    idx = np.arange(5)
    mydictidx = utils.select_indices(mydict, idx)
    np.testing.assert_allclose(mydictidx['a'], np.arange(5))
    np.testing.assert_allclose(mydictidx['b'], np.linspace(0, 1, 10)[:5])

    idx = np.array([1, 0, 1, 0, 1, 0, 1, 0, 1, 0]) > 0.5
    mydictidx = utils.select_indices(mydict, idx)
    np.testing.assert_allclose(mydictidx['a'], np.arange(0, 10, 2))
    np.testing.assert_allclose(mydictidx['b'], np.linspace(0, 1, 10)[0:10:2])

  def test_get_features(self):
    """Test extraction of features."""
    for k in [1, 5, 10, 15]:
      for add_loss in [True, False]:
        feats = utils.get_features(
            self.mydict, 'logits', top_k=k, add_loss=add_loss)
        k_selected = min(k, 14)
        self.assertEqual(feats.shape, (1000, k_selected + int(add_loss)))

  def test_subsample_to_balance(self):
    """Test subsampling of two arrays."""
    feats = utils.subsample_to_balance(self.mydict, random_state=23)

    train = np.sum(self.mydict['is_train'])
    test = 1000 - train
    n_chosen = min(train, test)
    self.assertEqual(feats['logits'].shape, (2 * n_chosen, 14))
    self.assertEqual(feats['loss'].shape, (2 * n_chosen,))
    self.assertEqual(np.sum(feats['is_train']), n_chosen)
    self.assertEqual(np.sum(1 - feats['is_train']), n_chosen)

  def test_get_data(self):
    """Test train test split data generation."""
    for test_size in [0.2, 0.5, 0.8, 0.55555]:
      (x_train, y_train), (x_test, y_test) = utils.get_train_test_split(
          self.mydict, add_loss=True, test_size=test_size)
      n_test = int(test_size * 1000)
      n_train = 1000 - n_test
      self.assertEqual(x_train.shape, (n_train, 11))
      self.assertEqual(y_train.shape, (n_train,))
      self.assertEqual(x_test.shape, (n_test, 11))
      self.assertEqual(y_test.shape, (n_test,))


if __name__ == '__main__':
  absltest.main()
