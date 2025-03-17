"""
Secret data masking module.
"""

import copy
import os


class LearnedError(Exception):
    """
    Raised when a new value is learned, to run masking again.
    """
    pass


class Mask:
    """
    Masking object that can learn values.

    .. code-block:: python

        mask = cli2.Mask(keys=['password'], values=['secretval'])
        result = mask(dict(password='xx', text='some secretval noise xx'))

    Will cause result to be:

    .. code-block:: yaml

        password: ***MASKED***
        text: some ***MASKED*** noise ***MASKED***

    Because:

    - ``secretval`` was given as a value to mask
    - ``password``'s value because ``password`` was given as a key to match
    - the Mask object learned the value of the ``password`` key, and masked it
      in ``text``

    .. py:attribute:: keys

        Set of keys that contain values to mask

    .. py:attribute:: values

        Set of values to mask

    .. py:attribute:: renderer

        Optionnal callback to render discovered values to mask

    .. py:attribute:: debug

        Enabled by the :envvar:`DEBUG` environment variable, makes this a no-op
        (don't mask anything).
    """

    def __init__(self, keys=None, values=None, renderer=None, debug=False):
        self.keys = set(keys) if keys else set()
        self.values = set(values) if values else set()
        self.renderer = renderer
        if os.getenv('DEBUG'):
            self.debug = True
        else:
            self.debug = debug

    def __call__(self, data):
        """"
        Do our best to mask sensitive values in the data param recursively,
        returning a masked copy of the passed data.

        - when data is a dict: it is recursively iterated on, any value that in
          is :py:attr:`keys` will have it's value replaced with
          ``***MASKED***``, also, the value is added to
          :py:attr:`values`.
        - when data is a string, each :py:attr:`values` will be replaced
          with ``***MASKED***``, so we're actually able to mask sensitive
          information from stdout outputs and the likes.
        - when data is a list, each item is passed to :py:meth:`_mask()`.

        Note that the :envvar:`DEBUG` environment variable will prevent any
        masking at all.

        :param data: Any kind of data to mask, will return a deepcopy of that.
        """
        if self.debug:
            return data

        while True:
            try:
                return self._mask(copy.deepcopy(data))
            except LearnedError:
                continue
            else:
                break

    def _mask(self, data):
        """
        Actual, in-place masking method.
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key in self.keys:
                    if self.renderer:
                        value = self.renderer(value)
                    if value not in self.values:
                        self.values.add(value)
                        raise LearnedError()
                    data[key] = '***MASKED***'
                else:
                    data[key] = self._mask(value)
        elif isinstance(data, list):
            return [self._mask(item) for item in data]
        elif isinstance(data, set):
            return {self._mask(item) for item in data}
        elif isinstance(data, str):
            for value in sorted(self.values, key=len, reverse=True):
                data = data.replace(str(value), '***MASKED***')
        return data

    def __repr__(self):
        result = 'Mask(keys=[' + ', '.join(self.keys) + ']'
        if self.values:
            result += f', number_of_values={len(self.values)}'
        return result + ')'

    def __bool__(self):
        return bool(self.keys or self.values)
