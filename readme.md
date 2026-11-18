# Trabajo chungo de crear un agente

usamos JSON para comunicar un agente con un modelo de lenguaje.

con este modelo en concreto recibirá una lista; el contenido que responde el modelo, habra una 
lista de instancias. 

Si es una lista, operamos de otra lista, Si len > 0 m si el contenido en la pos 0 de las lista accedemos a el y obtenemos ese texto de ese sitio (es una
medida de precaucion por si tuvieramos que poner a este agente a trabajar contra un modelo diferente).

otra precaucion es no fiarse de lo que le hemos dicho en el primpt del sistema "solo responde con amtematico o con poeta", esta comprobando si nos fijamos que el 
string matematico esté en el texto. para garantizarse de que funciona (prueba que esta en l arepuesta del LLM).

## cual es el next agent

return next_agent: destino



