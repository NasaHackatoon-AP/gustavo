class ConversaContexto:
    """
    Guarda informações do usuário para manter contexto da conversa.
    Agora gerencia histórico separado por usuário.
    """
    def __init__(self):
        self.historico_usuarios = {}  # {usuario_id: [mensagens]}
        self.locais_usuarios = {}  # {usuario_id: local}

    def adicionar(self, usuario_id: str, mensagem_usuario: str, resposta_bot: str):
        if usuario_id not in self.historico_usuarios:
            self.historico_usuarios[usuario_id] = []
        self.historico_usuarios[usuario_id].append({"usuario": mensagem_usuario, "bot": resposta_bot})

    def definir_local(self, usuario_id: str, local: str):
        self.locais_usuarios[usuario_id] = local

    def obter_local(self, usuario_id: str):
        return self.locais_usuarios.get(usuario_id)

    def obter_historico(self, usuario_id: str):
        return self.historico_usuarios.get(usuario_id, [])