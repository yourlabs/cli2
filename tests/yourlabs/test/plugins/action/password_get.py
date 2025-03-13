import cansible


class ActionModule(cansible.ActionBase):
    async def run_async(self):
        def secret_extract(result):
            _, self.secret, _ = result['stdout'].split(':')
            self.mask_values.add(self.secret)

        result = self.subprocess_remote(
            'echo foo:p455w0RD:bar',
            callback=secret_extract
        )
        self.result['secret'] = self.secret
        self.result['stdout'] = result['stdout']
