class ConversaContexto:
    """
    Guarda informações do usuário para manter contexto da conversa.
    """
    def __init__(self):
        self.historico = []
        self.local_atual = None  # placeholder para cidade/local do usuário

    def adicionar(self, mensagem_usuario: str, resposta_bot: str):
        self.historico.append({"usuario": mensagem_usuario, "bot": resposta_bot})

    def definir_local(self, local: str):
        self.local_atual = local

    def obter_local(self):
        return self.local_atual

    def obter_historico(self):
        return self.historico