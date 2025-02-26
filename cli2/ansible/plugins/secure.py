from __future__ import annotations
import os

DOCUMENTATION = '''
    name: secure
    type: stdout
    short_description: YAML Ansible screen output with variable masking
    version_added: "2.0"
    options:
      mask:
        name: Comma-separated list of variables to mask
        description:
          - Replace matching key values with ***MASKED***
        type: str
        default: json
        env:
          - name: ANSIBLE_MASK
        ini:
          - key: mask
            section: defaults
    extends_documentation_fragment:
      - default_callback
      - result_format_callback
    description:
    - example
'''
from ansible.plugins.callback.default import CallbackModule


class CallbackModule(CallbackModule):
    CALLBACK_VERSION = 1.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'secure'

    def _dump_results(self, result, indent=None, sort_keys=True,
                      keep_invocation=False, serialize=True):
        mask = self.get_option('mask').split(',')

        def _mask(data):
            for key, value in data.items():
                if isinstance(value, dict):
                    data[key] = _mask(value)
                elif key in mask:
                    data[key] = '***MASKED***'
            return data

        return super()._dump_results(
            result, indent=indent, sort_keys=sort_keys,
            keep_invocation=keep_invocation, serialize=serialize,
        )
