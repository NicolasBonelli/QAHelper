from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core import VectorStoreIndex
from backend.utils.db_actions import  create_index_from_pg, save_chunks_to_db
from backend.utils.db_connection import SessionLocal
from backend.models.db import DocumentEmbedding
import uuid
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def chunk_faq_recursive(text: str, doc_id: str = None):
    """
    Chunker recursivo para FAQs con RecursiveCharacterTextSplitter para optimizar almacenamiento en BD
    Args:
        text: Texto a procesar
        doc_id: ID del documento (si no se proporciona, se genera uno)
    Returns:
        doc_id: ID del documento procesado
    """
    if doc_id is None:
        doc_id = str(uuid.uuid4())
    
    doc = Document(text=text)
    
    # Usar RecursiveCharacterTextSplitter con mínima superposición para optimizar BD
    chunker = SentenceSplitter(
        chunk_size=120,  # Tamaño óptimo para BD
        chunk_overlap=5,  # Mínima superposición para mantener contexto
    )
    
    nodes = chunker.get_nodes_from_documents([doc])
    
    # Embeddings con modelo e5-base-v2 para similitud semántica
    embed_model = HuggingFaceEmbedding(model_name="intfloat/e5-base-v2")
    embeddings = embed_model.get_text_embedding_batch([n.text for n in nodes])
    
    # Asignar embeddings a cada nodo
    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding
    
    # Guardar chunks en la base de datos
    print(f"💾 Guardando {len(nodes)} chunks en PostgreSQL...")
    save_chunks_to_db(nodes, doc_id)
    print(f"✅ Chunks guardados exitosamente con doc_id: {doc_id}")
    
    return doc_id


def retrieve_chunks(query: str, top_k: int = 5):
    index = create_index_from_pg()
    retriever = index.as_retriever(similarity_top_k=top_k)

    results = retriever.retrieve(query)

    for i, res in enumerate(results):
        print(f"{i+1}. Score: {res.score:.3f} - Texto: {res.text[:100]}...")

    return results


def process_and_store_faqs(faq_text: str, doc_id: str = None):
    """
    Función principal para procesar FAQs y almacenarlas en la base de datos
    Args:
        faq_text: Texto de las FAQs
        doc_id: ID del documento (opcional)
    Returns:
        doc_id: ID del documento procesado
    """
    try:
        print("🔄 Procesando FAQs y almacenando en PostgreSQL...")
        doc_id = chunk_faq_recursive(faq_text, doc_id)
        print(f"✅ FAQs procesadas y almacenadas. Doc ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"❌ Error procesando FAQs: {e}")
        return None

# Ejemplo de uso
faq_texto = """
Pregunta: ¿Qué es el producto AIStart?
Respuesta: AIStart es una plataforma integral de inteligencia artificial diseñada para ayudar a startups, pequeñas y medianas empresas a automatizar y optimizar procesos clave de negocio. A través de un conjunto de herramientas modulares, AIStart permite implementar soluciones de machine learning, procesamiento de lenguaje natural y análisis predictivo sin necesidad de conocimientos técnicos avanzados. El sistema incluye un asistente virtual configurable, dashboards interactivos de métricas, herramientas de análisis de datos en tiempo real y funciones de integración con aplicaciones externas. AIStart se ha desarrollado con un enfoque en la escalabilidad, permitiendo que una empresa comience con funcionalidades básicas y, a medida que crezca, incorpore módulos adicionales sin interrumpir la operación.

Pregunta: ¿Cómo se integra AIStart con otras herramientas?
Respuesta: AIStart ofrece una API RESTful documentada y fácil de usar, que permite la integración con más de 200 aplicaciones y servicios populares, como CRMs, ERPs, plataformas de comercio electrónico, servicios de almacenamiento en la nube y sistemas de mensajería. Además, cuenta con conectores nativos para herramientas como Salesforce, HubSpot, Slack, Trello, Google Workspace, Microsoft Teams, Shopify y Zapier, lo que facilita la automatización de flujos de trabajo. También dispone de un SDK para desarrolladores en Python, JavaScript y Java, con ejemplos prácticos y plantillas para acelerar la implementación. La integración puede realizarse en pocos pasos y sin afectar la infraestructura existente.

Pregunta: ¿Es seguro usar AIStart con datos sensibles?
Respuesta: Sí. AIStart ha sido diseñado bajo estrictos estándares de seguridad y cumplimiento normativo, cumpliendo con regulaciones como GDPR, CCPA y ISO 27001. Todos los datos son encriptados en tránsito mediante TLS 1.3 y en reposo mediante AES-256. Además, la plataforma implementa autenticación multifactor (MFA), control granular de accesos y registros de auditoría para monitorear todas las interacciones. AIStart ofrece opciones de despliegue en la nube, en entornos híbridos y on-premises, lo que permite a las organizaciones mantener un control total sobre sus datos. También realiza pruebas de penetración periódicas y cuenta con un equipo interno de ciberseguridad que monitorea la infraestructura 24/7.

Pregunta: ¿Cuánto tiempo lleva implementar AIStart?
Respuesta: El tiempo de implementación depende del caso de uso, el número de integraciones necesarias y la complejidad de los procesos a automatizar. En promedio, las pequeñas empresas pueden tener el sistema operativo en menos de dos semanas, mientras que proyectos empresariales con integraciones complejas pueden tardar entre 4 y 8 semanas. AIStart proporciona un equipo de onboarding especializado que acompaña a cada cliente en el proceso, desde la configuración inicial, la migración de datos, la capacitación de usuarios y la personalización de flujos de trabajo, hasta la puesta en marcha oficial.

Pregunta: ¿Qué tipo de soporte técnico ofrece AIStart?
Respuesta: AIStart cuenta con soporte técnico multicanal disponible 24/7 a través de chat en vivo, correo electrónico y teléfono. Además, los clientes tienen acceso a una base de conocimientos con guías paso a paso, tutoriales en video, webinars semanales y un foro comunitario moderado por expertos. Los planes empresariales incluyen un Customer Success Manager asignado, soporte prioritario y revisiones trimestrales de rendimiento del sistema para garantizar que la solución siga alineada con los objetivos de negocio.

Pregunta: ¿AIStart es compatible con dispositivos móviles?
Respuesta: Sí. AIStart cuenta con aplicaciones nativas para iOS y Android, así como una versión web optimizada para móviles. Esto permite que los usuarios accedan a sus paneles de control, reportes y herramientas de automatización desde cualquier lugar, manteniendo la seguridad y el rendimiento. Las apps móviles incluyen notificaciones push personalizables, acceso seguro mediante biometría (huella dactilar o reconocimiento facial) y sincronización automática con la versión de escritorio.

Pregunta: ¿Cuáles son las principales ventajas de AIStart frente a sus competidores?
Respuesta: AIStart destaca por su facilidad de uso, tiempo de implementación reducido, alto nivel de personalización y capacidad para integrarse de forma nativa con un amplio ecosistema de herramientas empresariales. Su arquitectura modular permite que las empresas paguen únicamente por los módulos que necesitan, evitando costes innecesarios. Además, incluye funciones avanzadas como análisis predictivo en tiempo real, generación automática de reportes, workflows inteligentes con IA y soporte multilingüe.

Pregunta: ¿AIStart ofrece planes de precios flexibles?
Respuesta: Sí. AIStart cuenta con un modelo de precios escalable basado en suscripción mensual o anual, con planes que van desde una versión básica para startups hasta opciones empresariales con todas las funcionalidades. Los clientes pueden cambiar de plan en cualquier momento y pagar únicamente por los módulos que utilicen. También se ofrecen descuentos por volumen y precios especiales para organizaciones sin fines de lucro y proyectos educativos.

Pregunta: ¿Puede AIStart adaptarse a sectores específicos?
Respuesta: Sí. AIStart ha sido implementado con éxito en sectores como salud, educación, retail, logística, finanzas y tecnología. Cada sector cuenta con plantillas y modelos de IA preconfigurados para acelerar la puesta en marcha. Por ejemplo, en el sector salud se incluyen módulos para gestión de citas y análisis de historiales médicos; en retail, herramientas de predicción de inventario y segmentación de clientes; y en educación, sistemas de evaluación automatizada y analítica de desempeño estudiantil.

Pregunta: ¿Qué tipo de IA utiliza AIStart?
Respuesta: AIStart combina diferentes enfoques de inteligencia artificial, incluyendo redes neuronales profundas para análisis predictivo, procesamiento de lenguaje natural (NLP) para chatbots y análisis de texto, y modelos de machine learning supervisado y no supervisado para clasificación, segmentación y detección de patrones. Además, la plataforma soporta modelos personalizados entrenados por el cliente e incluso permite la integración con APIs externas de IA como OpenAI, Google Vertex AI o Amazon SageMaker.

Pregunta: ¿AIStart se actualiza de forma automática?
Respuesta: Sí. Todas las actualizaciones de la plataforma, tanto de seguridad como de funcionalidad, se realizan de forma automática y sin interrupciones para el usuario. Las actualizaciones mayores se comunican con antelación y se implementan en ventanas de mantenimiento programadas para minimizar cualquier impacto.

Pregunta: ¿Puedo probar AIStart antes de comprarlo?
Respuesta: Sí. AIStart ofrece una prueba gratuita de 14 días con acceso a todas las funcionalidades. Durante este período, el cliente recibe soporte técnico y puede evaluar el rendimiento, la facilidad de uso y la capacidad de integración con sus procesos. Al finalizar la prueba, el cliente puede elegir un plan de pago o cancelar sin compromiso.
Pregunta: ¿Cuáles son algunos casos de éxito o ejemplos concretos de uso de AIStart?
Respuesta: AIStart ha ayudado a diversas empresas. Por ejemplo, una startup de e-commerce utilizó AIStart para optimizar la gestión de inventario y predecir la demanda de productos, lo que redujo los costes de almacenamiento en un 25%. Una cadena de restaurantes implementó el asistente virtual para gestionar reservas y responder a preguntas frecuentes de los clientes, mejorando la satisfacción en un 30%. Por su parte, una empresa de logística usó AIStart para optimizar rutas de entrega, lo que disminuyó los tiempos de tránsito y el consumo de combustible.

Pregunta: ¿Qué nivel de personalización se puede lograr con las herramientas de AIStart?
Respuesta: La plataforma está diseñada para ser altamente personalizable. Los usuarios pueden adaptar los flujos de trabajo, crear dashboards con métricas específicas, configurar el asistente virtual con respuestas y tonos de voz personalizados, y entrenar modelos de machine learning con sus propios datos. También pueden ajustar los permisos de acceso para diferentes roles de usuario y personalizar las notificaciones y reportes automáticos.

Pregunta: ¿Cómo puedo entrenar un modelo de IA con mis propios datos en AIStart?
Respuesta: AIStart ofrece una interfaz de usuario intuitiva para el entrenamiento de modelos. Simplemente debes subir tus datos en formatos comunes como CSV o Excel, definir los parámetros clave y la plataforma se encargará de preprocesar los datos y entrenar el modelo. También puedes usar las plantillas de modelos predefinidos de AIStart como punto de partida y ajustarlos con tus datos para obtener resultados más precisos.

Pregunta: ¿AIStart tiene alguna limitación de tamaño de datos o número de usuarios?
Respuesta: La arquitectura de AIStart es escalable, por lo que no hay límites estrictos. Los planes empresariales y personalizados están diseñados para manejar grandes volúmenes de datos y un número ilimitado de usuarios. El rendimiento de la plataforma se mantiene gracias a una infraestructura de nube elástica que se ajusta a la demanda.

Pregunta: ¿Cómo puedo migrar mis datos actuales a la plataforma de AIStart?
Respuesta: El equipo de onboarding de AIStart asiste en todo el proceso de migración de datos. Ofrecemos herramientas de importación masiva para datos estructurados y no estructurados, y nuestros conectores nativos facilitan la sincronización con fuentes externas. Para proyectos más complejos, se puede usar la API para automatizar la migración y garantizar la integridad de los datos.

Pregunta: ¿Qué métricas o KPIs puedo monitorear con AIStart?
Respuesta: AIStart permite monitorear una amplia gama de métricas en tiempo real. Esto incluye KPIs de ventas, como la tasa de conversión y el valor de vida del cliente; métricas de marketing, como el retorno de la inversión publicitaria; KPIs de operaciones, como la eficiencia de la cadena de suministro y el rendimiento de los equipos. Todos los datos se visualizan en dashboards personalizables con gráficos y tablas fáciles de entender.

Pregunta: ¿Qué medidas toma AIStart para garantizar la privacidad y el uso ético de la IA?
Respuesta: AIStart se compromete con la privacidad y la ética. La plataforma cumple con los principios de transparencia y rendición de cuentas, permitiendo que los usuarios comprendan cómo se toman las decisiones de la IA. Los datos se anonimizan y se utilizan de manera responsable para entrenar los modelos. Además, la plataforma no utiliza datos personales sensibles para fines publicitarios ni los comparte con terceros sin el consentimiento explícito del usuario.

Pregunta: ¿Cómo se asegura AIStart de que los modelos de IA sean precisos?
Respuesta: La plataforma ofrece herramientas de evaluación y monitoreo de modelos de IA. Esto permite a los usuarios ver la precisión, la confianza y el rendimiento del modelo a lo largo del tiempo. AIStart también envía alertas automáticas si detecta una degradación en el rendimiento del modelo, lo que permite a los usuarios retrainarlo o ajustarlo con datos más recientes.

Pregunta: ¿AIStart puede integrarse con sistemas de terceros que no tengan una API?
Respuesta: AIStart se integra principalmente a través de APIs. Sin embargo, para sistemas heredados o sin una API moderna, el equipo de soporte de AIStart puede explorar soluciones de integración personalizadas utilizando conectores de terceros como Zapier o herramientas de automatización de procesos robóticos (RPA), que pueden simular las interacciones de un usuario para automatizar tareas.

Pregunta: ¿Se necesita un equipo de TI especializado para gestionar AIStart?
Respuesta: No, la plataforma está diseñada para ser utilizada por equipos de negocio sin necesidad de un equipo de TI o científicos de datos dedicados. La interfaz intuitiva y las herramientas de bajo código permiten a los usuarios crear, implementar y gestionar soluciones de IA de manera autónoma. No obstante, para proyectos empresariales o muy complejos, el equipo de soporte de AIStart y el Customer Success Manager están siempre disponibles para ofrecer asistencia técnica y estratégica.
    """

if __name__ == "__main__":
    print("➡️ Procesando chunks recursivos con embeddings...")
    
    # Procesar y almacenar FAQs en PostgreSQL
    

    
    # Test del retrieval desde la BD
    print("\n🧪 Probando sistema de retrieval desde PostgreSQL...")
    query_test = "¿Qué KPIs puede usar AIStart?"
    top_chunks = retrieve_chunks(query_test, top_k=3)
    
    if top_chunks:
        print(f"✅ Top {len(top_chunks)} chunks encontrados para: '{query_test}'")
        for i, chunk in enumerate(top_chunks):
            print(f"  {i+1}. Score: {chunk.score:.3f} - Texto: {chunk.text[:100]}...")
    else:
        print("❌ No se encontraron chunks relevantes")

