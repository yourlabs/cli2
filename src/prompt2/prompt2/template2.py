import template2


class PromptTemplatePlugin(template2.Plugin):
    def macros(self):
        return dict(prompt2='prompt2.macros.txt')
