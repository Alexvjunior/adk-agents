import os
import requests
import logging
import base64
from typing import Optional, Dict, Any
from urllib.parse import quote
from agno.tools.toolkit import Toolkit
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class EvolutionApiConfig(BaseModel):
    """Configuração para Evolution API"""
    server_url: str = Field(description="URL do servidor Evolution API")
    api_key: str = Field(description="Chave da API")
    instance: str = Field(description="Nome da instância")


class EvolutionApiTools(Toolkit):
    """Ferramentas para Evolution API - Envio de mensagens WhatsApp"""

    def __init__(
        self,
        server_url: Optional[str] = None,
        api_key: Optional[str] = None,
        instance: Optional[str] = None,
    ):
        """
        Inicializa as ferramentas da Evolution API
        
        Args:
            server_url: URL do servidor Evolution API
            api_key: Chave da API 
            instance: Nome da instância
        """
        super().__init__(name="evolution_api")
        
        # Configurar credenciais via parâmetros ou variáveis de ambiente
        self.config = EvolutionApiConfig(
            server_url=server_url or os.getenv("EVOLUTION_API_URL", ""),
            api_key=api_key or os.getenv("EVOLUTION_API_KEY", ""),
            instance=instance or os.getenv("EVOLUTION_INSTANCE", "")
        )
        
        required_fields = [
            self.config.server_url, 
            self.config.api_key, 
            self.config.instance
        ]
        if not all(required_fields):
            raise ValueError(
                "Configuração incompleta da Evolution API. "
                "Forneça server_url, api_key e instance via parâmetros "
                "ou variáveis de ambiente."
            )

        self.register(self.send_text_message)
        self.register(self.send_media_message)
        self.register(self.check_whatsapp_number)

    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers para requisições"""
        return {
            "Content-Type": "application/json",
            "apikey": self.config.api_key
        }

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Faz requisição para a Evolution API"""
        # URL encode o endpoint para lidar com espaços e caracteres especiais
        url = f"{self.config.server_url.rstrip('/')}/{quote(endpoint, safe='/')}"
        
        try:
            response = requests.post(
                url,
                json=data,
                headers=self._get_headers(),
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para Evolution API: {e}")
            error_msg = (
                f"Falha na comunicação com Evolution API: {str(e)}"
            )
            raise Exception(error_msg)

    def send_text_message(
        self, 
        number: str, 
        text: str, 
        delay: Optional[int] = None
    ) -> str:
        """
        Envia mensagem de texto via WhatsApp
        
        Args:
            number: Número do destinatário (formato: 5511999999999)
            text: Texto da mensagem
            delay: Delay em milissegundos (opcional)
            
        Returns:
            ID da mensagem enviada ou erro
        """
        try:
            # Validar número (deve ter código do país)
            if not number.startswith("55") or len(number) < 12:
                return ("❌ Número inválido. Use formato: 5511999999999 "
                        "(com código do país)")
            
            endpoint = f"message/sendText/{self.config.instance}"
            
            data = {
                "number": number,
                "text": text
            }
            
            if delay:
                data["options"] = {"delay": delay}
            
            response = self._make_request(endpoint, data)
            
            # Extrair ID da mensagem
            message_id = response.get("key", {}).get("id", "Desconhecido")
            status = response.get("status", "Desconhecido")
            
            result = (
                "✅ Mensagem enviada com sucesso!\n"
                f"📱 Para: {number}\n"
                f"🆔 ID: {message_id}\n"
                f"📊 Status: {status}"
            )
            return result
            
        except Exception as e:
            logger.error("Erro ao enviar mensagem de texto: %s", e)
            return "❌ Erro ao enviar mensagem: " + str(e)

    def send_media_message(
        self, 
        number: str, 
        media_type: str, 
        media: str, 
        file_name: Optional[str] = None,
        caption: Optional[str] = None,
        delay: Optional[int] = None
    ) -> str:
        """
        Envia mensagem de mídia via WhatsApp
        
        Args:
            number: Número do destinatário (formato: 5511999999999)
            media_type: Tipo de mídia (image, video, audio, document)
            media: Conteúdo da mídia (base64) OU caminho para arquivo local
            file_name: Nome do arquivo (opcional)
            caption: Legenda da mídia (opcional)
            delay: Delay em milissegundos (opcional)
            
        Returns:
            ID da mensagem enviada ou erro
        """
        try:
            # Validar número
            if not number.startswith("55") or len(number) < 12:
                return ("❌ Número inválido. Use formato: 5511999999999 "
                        "(com código do país)")
            
            # Validar tipo de mídia
            valid_types = ["image", "video", "audio", "document"]
            if media_type not in valid_types:
                types_str = ', '.join(valid_types)
                return f"❌ Tipo de mídia inválido. Use: {types_str}"
            
            # Verificar se media é um caminho de arquivo ou base64
            media_base64 = media
            if media.startswith('knowledge/') or '/' in media or '\\' in media:
                # É um caminho de arquivo - converter para base64
                try:
                    import base64
                    import os
                    
                    if not os.path.exists(media):
                        return f"❌ Arquivo não encontrado: {media}"
                    
                    with open(media, 'rb') as file:
                        media_content = file.read()
                        media_base64 = base64.b64encode(media_content).decode('utf-8')
                        
                    logger.info(f"✅ Arquivo {media} convertido para base64 ({len(media_base64)} chars)")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao ler arquivo {media}: {e}")
                    return f"❌ Erro ao ler arquivo {media}: {str(e)}"
            
            endpoint = f"message/sendMedia/{self.config.instance}"
            
            # Estrutura correta: campos diretos sem wrapper mediaMessage
            data = {
                "number": number,
                "mediatype": media_type,  # minúsculo, campo direto
                "media": media_base64
            }
            
            if file_name:
                data["fileName"] = file_name
            if caption:
                data["caption"] = caption
            
            if delay:
                data["options"] = {"delay": delay}
            
            response = self._make_request(endpoint, data)
            
            # Extrair informações da resposta
            message_id = response.get("key", {}).get("id", "Desconhecido")
            status = response.get("status", "Desconhecido")
            
            result = (
                "✅ Mídia enviada com sucesso!\n"
                f"📱 Para: {number}\n"
                f"🎬 Tipo: {media_type}\n"
                f"🆔 ID: {message_id}\n"
                f"📊 Status: {status}"
            )
            return result
            
        except Exception as e:
            logger.error("Erro ao enviar mídia: %s", e)
            return "❌ Erro ao enviar mídia: " + str(e)

    def check_whatsapp_number(self, number: str) -> str:
        """
        Verifica se um número está no WhatsApp
        
        Args:
            number: Número para verificar (formato: 5511999999999)
            
        Returns:
            Status do número no WhatsApp
        """
        try:
            endpoint = f"chat/whatsappNumbers/{self.config.instance}"
            
            data = {
                "numbers": [number]
            }
            
            response = self._make_request(endpoint, data)
            
            # Processar resposta
            if response and len(response) > 0:
                number_info = response[0]
                exists = number_info.get("exists", False)
                jid = number_info.get("jid", "")
                
                if exists:
                    return f"✅ Número {number} está no WhatsApp\n🆔 JID: {jid}"
                else:
                    return f"❌ Número {number} não está no WhatsApp"
            else:
                return f"❓ Não foi possível verificar o número {number}"
                
        except Exception as e:
            logger.error(f"Erro ao verificar número WhatsApp: {e}")
            return f"❌ Erro ao verificar número: {str(e)}"


# Funções auxiliares para conversão de arquivos
def file_to_base64(file_path: str) -> str:
    """
    Converte arquivo para base64
    
    Args:
        file_path: Caminho para o arquivo
        
    Returns:
        String base64 do arquivo
    """
    try:
        with open(file_path, "rb") as file:
            file_content = file.read()
            base64_string = base64.b64encode(file_content).decode('utf-8')
            return base64_string
    except Exception as e:
        raise Exception(f"Erro ao converter arquivo para base64: {str(e)}")


def url_to_base64(url: str) -> str:
    """
    Baixa arquivo de URL e converte para base64
    
    Args:
        url: URL do arquivo
        
    Returns:
        String base64 do arquivo
    """
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        base64_string = base64.b64encode(response.content).decode('utf-8')
        return base64_string
    except Exception as e:
        raise Exception(f"Erro ao baixar e converter URL: {str(e)}")


# Exemplo de uso
if __name__ == "__main__":
    # Configuração via variáveis de ambiente
    evolution_tools = EvolutionApiTools()
    
    # Teste de envio de mensagem
    result = evolution_tools.send_text_message(
        number="5511999999999",
        text="Olá! Esta é uma mensagem de teste da Evolution API."
    )
    print(result) 