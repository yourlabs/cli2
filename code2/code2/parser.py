class Parser:
    def __init__(self, model):
        self.model = model

    def messages(self, messages):
        return messages


class Wholefile(Parser):
    system = "Respond only with the complete new file content, as this will be directly written to the file by an automated AI assistant tool—no additional text, comments, or explanations are allowed."  # noqa

    def messages(self, messages):
        messages.append(
            dict(
                role='system',
                content=self.system,
            ),
        )
        return messages

    def parse(self, response):
        if response.startswith('```'):
            # strip markup the IA absolutely wants to add
            return '\n'.join([l for l in response.split('\n')[1:-1]])
        return response
