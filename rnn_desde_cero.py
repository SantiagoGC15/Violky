# -*- coding: utf-8 -*-
"""Copy of RNN Scratch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/17QhHGaGeDnAi1rRz5N1jN1_s8zPn2zLN
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import math 
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.metrics import mean_squared_error
# %matplotlib inline
plt.rcParams['figure.figsize'] = (10, 5)
plt.style.use('ggplot')
plt.rcParams["legend.loc"]='best'

df = pd.read_csv('/content/drive/MyDrive/Tesis/Base de datos/DCOILWTICO2015.csv')
df.drop(df[df['DCOILWTICO'] == '.'].index, inplace = True)
df.dropna(inplace=True)
df['DATE']=pd.to_datetime(df['DATE'], format='%Y-%m-%d')
df = df.set_index('DATE')
df['DCOILWTICO']=df['DCOILWTICO'].astype(float)

"""## Violky sin Bias"""

class ViolkyRNN(object):
  
  def __init__(self,num_entradas=3, num_caoculta=2, num_salida=1, activacion='tanh',perdida='RMSE', metrica='MSE', optimizador='SGD', bptt_truncate = 5, min_clip_val = -10,  max_clip_val = 10):
    self.num_entradas=num_entradas
    self.num_caoculta=num_caoculta
    self.num_salida=num_salida
    self.bptt_truncate=bptt_truncate
    self.min_clip_val= min_clip_val
    self.max_clip_val=max_clip_val

    U = np.random.uniform(0, 1, (self.num_caoculta, self.num_entradas))
    V = np.random.uniform(0, 1, (self.num_entradas, self.num_caoculta)) 
    W = np.random.uniform(0, 1, (self.num_caoculta, self.num_caoculta)) 
    self.U=U
    self.V=V
    self.W=W
    

    def tanh(x):return np.tanh(x)

    def d_tanh(x): return 1 - np.square(np.tanh(x))

    def sigmoid(x): return 1/(1 + np.exp(-x))

    def d_sigmoid(x): return (1 - sigmoid(x))*sigmoid(x)

    def softplus(x): return np.log(1+np.exp(x))

    def logisticF(x): return np.exp(x)/(1+np.exp(x))

    def d_logisticF(x): return np.exp(x)/((1+np.exp(x))**2)

    def gauss(x, sigma=2 , c=0): return np.exp(-(x-c)**2/(2*sigma**2))

    def d_gauss(x, A=1, B=1): return -2*np.exp(-B*(x)**2)*A*B*x

    def sen(x,A=1,O=1,B=0): return A*np.sin(O*x+B)

    def d_sen(x,A=1,O=1,B=1): return A*np.cos(O*x+B)*O
    
    def relu(x): return max(0,x)

    def d_relu(x): 
      if x>=0:
         return 1
      else:
        return 0
    def prelu(x,p): return max(0,x)+p*min(0,x)

    def d_prelu(x):
      if x>0:
        return 0
      else:
        return x
    FuncionesActivacion = {
        'tanh': (tanh, d_tanh),
        'sigmoid': (sigmoid, d_sigmoid),
        'sofplus' : (softplus,logisticF),
        'logistic': (logisticF,d_logisticF),
        'gauss':(gauss,d_gauss),
        'seno':(sen,d_sen),
        'relu':(relu,d_relu),
        'prelu':(prelu,d_prelu)
    }
    self.FuncionesActivacion =FuncionesActivacion 
    self.act, self.d_act = self.FuncionesActivacion.get(activacion)

    def MSE(y_hat, y_verdadero): return np.average((y_hat-y_verdadero)**2)
    def l_MSE(y,y_hat): return np.median(1/2*np.average((y-y_hat)**2))
    def d_MSE(y_hat, y_verdadero): return (2*(np.subtract(y_hat,y_verdadero)))/len(y_hat) 

    def RMSE(y_hat, y_verdadero): return np.sqrt(np.average((y_hat-y_verdadero)**2))
    def l_RMSE(y,y_hat): return np.sqrt(1/2*np.median(np.average((y-y_hat)**2)))
    def d_RMSE(y_hat, y_verdadero): return 1/(2*np.sqrt((2*abs(np.subtract(y_hat,y_verdadero)))/len(y_hat)))

    def SSE(y_hat, y_verdadero): return 1/2*(np.square(np.subtract(y_hat,y_verdadero)))
    def l_SSE(y,y_hat): return np.median(1/4*(np.square(np.subtract(y,y_hat))))
    def d_SSE(y_hat, y_verdadero): return np.subtract(y_hat,y_verdadero)

    Metricas = {
        'MSE': (MSE),
        'RMSE': (RMSE),
        'SSE': (SSE)
    }
    Perdidas = {
        'MSE': (l_MSE),
        'RMSE': (l_RMSE),
        'SSE': (SSE)
    }

    Derivadas ={
        'MSE': (d_MSE),
        'RMSE': (d_RMSE),
        'SSE': (d_SSE)     
    }
    
    self.Metricas = Metricas
    self.Derivadas = Derivadas
    self.Perdidas = Perdidas
    self.met = self.Metricas.get(metrica)
    self.l_met = self.Metricas.get(perdida)
    self.der = self.Derivadas.get(perdida)


    self.cachedU = np.zeros(self.U.shape)
    self.cachedV = np.zeros(self.V.shape)
    self.cachedW = np.zeros(self.W.shape)

    self.mU = np.zeros(self.U.shape)
    self.mtU = np.zeros(self.U.shape)
    self.vU = np.zeros(self.U.shape)
    self.vtU = np.zeros(self.U.shape)

    self.mV = np.zeros(self.V.shape)
    self.mtV = np.zeros(self.V.shape)
    self.vV = np.zeros(self.V.shape)
    self.vtV = np.zeros(self.V.shape)

    self.mW = np.zeros(self.W.shape)
    self.mtW = np.zeros(self.W.shape)
    self.vW = np.zeros(self.W.shape)
    self.vtW = np.zeros(self.W.shape)

    def SGD(tasa_aprendizaje, eps, beta1, beta2, alp, dU, dV, dW):
      self.U -=  tasa_aprendizaje*dU
      self.V -=  tasa_aprendizaje*dV
      self.W -=  tasa_aprendizaje*dW

    def Adagrad(tasa_aprendizaje, eps, beta1, beta2, alp, dU, dV, dW):
      self.cachedU += dU**2
      self.cachedV += dV**2
      self.cachedW += dW**2

      self.U -= tasa_aprendizaje*(dU/(np.sqrt(self.cachedU)+eps))
      self.V -=  tasa_aprendizaje*(dV/(np.sqrt(self.cachedV)+eps))
      self.W -=  tasa_aprendizaje*(dW/(np.sqrt(self.cachedW)+eps))


    def Momentum(tasa_aprendizaje, eps, beta1, beta2, alp, dU, dV, dW):
      self.cachedU += tasa_aprendizaje*dU
      self.cachedV += tasa_aprendizaje*dV
      self.cachedW += tasa_aprendizaje*dW

      self.U -= alp*self.cachedU
      self.V -=  alp*self.cachedV
      self.W -=  alp*self.cachedW


    def Adam(tasa_aprendizaje, eps, beta1, beta2, alp, dU, dV, dW):

      self.mU=beta1*self.mU+(1-beta1)*dU
      self.mtU=self.mU/(1-beta1)
      self.vU=beta2*self.vU+(1-beta2)*(dU**2)
      self.vtU=self.vU/(1-beta2)

      self.mV=beta1*self.mV+(1-beta1)*dV
      self.mtV=self.mV/(1-beta1)
      self.vV=beta2*self.vV+(1-beta2)*(dV**2)
      self.vtV=self.vV/(1-beta2)

      self.mW=beta1*self.mW+(1-beta1)*dW
      self.mtW=self.mW/(1-beta1)
      self.vW=beta2*self.vW+(1-beta2)*(dW**2)
      self.vtW=self.vW/(1-beta2)


      self.U -= (tasa_aprendizaje/(np.sqrt(self.vtU)+eps))*self.mtU
      self.V -=  (tasa_aprendizaje/(np.sqrt(self.vtV)+eps))*self.mtV
      self.W -=  (tasa_aprendizaje/(np.sqrt(self.vtW)+eps))*self.mtW


    Optimizador= {
      'SGD': SGD,
      'Adagrad': Adagrad ,
      'Momentum': Momentum ,
      'Adam': Adam
    }

    self.Optimizador=Optimizador
    self.actualizar_pesos=self.Optimizador.get(optimizador)

  def tanh(self,x): return np.tanh(x)

  def calcular_perdida(self,X, Y):
    perdida = 0
    metrica = 0
    for i in range(Y.shape[0]):
        x, y = X[i], Y[i]
        prev_activacion = np.zeros((self.num_caoculta, 1)) 
        for paso_tiempo in range(self.num_entradas):
            nueva_entrada = np.zeros(x.shape) 
            nueva_entrada[paso_tiempo] = x[paso_tiempo] 
            mulu = np.dot(self.U, nueva_entrada)
            mulw = np.dot(self.W, prev_activacion)
            sum = mulu+mulw
            activacion = sum
            mulv = self.act(np.dot(self.V, activacion))
            prev_activacion = activacion

        perdida_por_record = self.l_met(y,mulv)
        metrica_por_record = self.met(mulv,y)
        perdida += perdida_por_record/len(Y)
        metrica += metrica_por_record/len(Y) 
    return perdida, metrica, activacion

  def calc_layers(self,x, prev_activacion):
      capas = []
      for paso_tiempo in range(self.num_entradas):
          nueva_entrada = np.zeros(x.shape) 
          nueva_entrada[paso_tiempo] = x[paso_tiempo] 
          mulu = np.dot(self.U, nueva_entrada)
          mulw = np.dot(self.W, prev_activacion)
          sum = mulu+mulw
          activacion = sum
          mulv = self.act(np.dot(self.V, activacion))
          capas.append({'activacion': activacion, 'prev_activacion': prev_activacion})
          prev_activacion = activacion

      return capas, mulu, mulw, mulv

  def obtener_diferencial_de_activacion_anterior(self,sum, ds, W):
    d_sum = self.d_act(sum)*ds
    dmulw = d_sum*np.ones_like(ds)
    return np.dot(np.transpose(W), dmulw)

  def backprop(self,x, dmulv, mulu, mulw, capas):
      dU = np.zeros(self.U.shape)
      dV = np.zeros(self.V.shape)
      dW = np.zeros(self.W.shape)
      
      dU_t = np.zeros(self.U.shape)
      dV_t = np.zeros(self.V.shape)
      dW_t = np.zeros(self.W.shape)
      
      dU_i = np.zeros(self.U.shape)
      dW_i = np.zeros(self.W.shape)
      
      sum = mulu+mulw
      dsv = np.dot(np.transpose(self.V), dmulv)

      for paso_tiempo in range(self.num_entradas):
        dV_t = np.dot(dmulv, np.transpose(capas[paso_tiempo]['activacion']))
        ds = dsv
        dprev_activacion = self.obtener_diferencial_de_activacion_anterior(sum, ds, self.W)

        for _ in range(paso_tiempo-1, max(-1, paso_tiempo-self.bptt_truncate-1), -1):
            ds = dsv + dprev_activacion
            dprev_activacion = self.obtener_diferencial_de_activacion_anterior(sum, ds, self.W)
            dW_i = np.dot(self.W, capas[paso_tiempo]['prev_activacion'])
            
            nueva_entrada = np.zeros(x.shape)
            nueva_entrada[paso_tiempo] = x[paso_tiempo]
            dU_i = np.dot(self.U, nueva_entrada)
            
            dU_t += dU_i
            dW_t += dW_i
            
        dU += dU_t
        dV += dV_t
        dW += dW_t


        if dU.max() > self.max_clip_val: dU[dU > self.max_clip_val] = self.max_clip_val
        if dV.max() > self.max_clip_val: dV[dV > self.max_clip_val] =self. max_clip_val
        if dW.max() > self.max_clip_val: dW[dW > self.max_clip_val] = self.max_clip_val

        if dU.min() < self.min_clip_val:  dU[dU <self. min_clip_val] = self.min_clip_val
        if dV.min() < self.min_clip_val:  dV[dV < self.min_clip_val] = self.min_clip_val
        if dW.min() < self.min_clip_val:  dW[dW < self.min_clip_val] = self.min_clip_val
          
      return dU, dV, dW

  def entrenamiento(self, X, Y, X_validacion, Y_validacion, epocas, tasa_aprendizaje=0.0001, eps=1e-8, beta1=0.9,beta2=0.999, alp=0.9):
    plotPer=[]
    plotPerV=[]
    plotMet=[]
    plotMetV=[]

    for epoca in range(epocas):    
      perdida, metrica, prev_activacion = self.calcular_perdida(X, Y)

      val_perdida, val_metrica, _ = self.calcular_perdida(X_validacion, Y_validacion)

      plotPerV.append(val_perdida)
      plotMetV.append(val_metrica)
      plotPer.append(perdida)
      plotMet.append(metrica)

 
      for i in range(Y.shape[0]):
          x, y = X[i], Y[i]
          capas = []
          prev_activacion = np.zeros((self.num_caoculta, 1))
          capas, mulu, mulw, mulv = self.calc_layers(x, prev_activacion)
          dmulv = self.der(mulv,y)
          dU, dV, dW = self.backprop(x, dmulv, mulu, mulw, capas)

          self.actualizar_pesos(tasa_aprendizaje, eps, beta1, beta2, alp, dU, dV, dW)

      print(f'Epoca: {epoca+1}, Per_Entre: {perdida}, Per_Val: {val_perdida}, Met_Entre: {metrica}, Met_Val: {val_metrica}')
      historico=pd.DataFrame({'Perdida Entrenamiento': plotPer, 'Perdida Validación': plotPerV, 'Metrica Entrenamiento': plotMet, 'Metrica Validación': plotMetV})
        
    return historico

  def validacion(self, X, Y_validacion):
    val_predicciones = []
    for i in range(Y_validacion.shape[0]):
        x = X[i]
        prev_activacion = np.zeros((self.num_caoculta,1))

        for paso_tiempo in range(self.num_entradas):
            mulu = np.dot(self.U, x)
            mulw = np.dot(self.W, prev_activacion)
            sum = mulu + mulw
            activacion = self.tanh(sum)
            mulv = self.act(np.dot(self.V, activacion))
            prev_activacion = activacion
        val_predicciones.append(mulv)

    val_predicciones = np.array(val_predicciones)

    return val_predicciones[:, 0,0].reshape(Y_validacion.shape[0],1)

  def val(self, X):
    val_predicciones = []
    for i in range(X.shape[0]):
        x = X[i]
        prev_activacion = np.zeros((self.num_caoculta,1))
        for paso_tiempo in range(self.num_entradas):
            mulu = np.dot(self.U, x)
            mulw = np.dot(self.W, prev_activacion)
            sum = mulu + mulw
            activacion = self.tanh(sum)
            mulv = self.act(np.dot(self.V, activacion))
            prev_activacion = activacion
        val_predicciones.append(mulv)

    val_predicciones = np.array(val_predicciones)

    return val_predicciones[:, 0,0].reshape(X.shape[0],1)

  def seriesup(self,datos, numen=1, numsal=1, a=-1, b=1, dropnan=True):
      n_vars = 1 if type(datos) is list else datos.shape[1]
      df = pd.DataFrame(datos)
      cols, nombres = list(), list()
      for i in range(numen, 0, -1):
          cols.append(df.shift(i))
          nombres += [('x%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
      for i in range(0, numsal):
          cols.append(df.shift(-i))
          if i == 0:
              nombres += [('y%d(t)' % (j+1)) for j in range(n_vars)]
          else:
              nombres += [('y%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
      agg = pd.concat(cols, axis=1)
      agg.columns = nombres
      if dropnan:
          agg.dropna(inplace=True)
      return agg

  def validatest(self,datos,porcentaje=80):
    Da_to=df.shape[0]
    Da_entre=round((Da_to*porcentaje)/100)
    valores = datos.values
    entrenamiento = valores[:Da_entre, :]
    test = valores[Da_entre:, :]
    x_entrenamiento, y_entrenamiento = entrenamiento[:, :-1], entrenamiento[:, -1]
    x_val, y_val = test[:, :-1], test[:, -1]
    x_entrenamiento = x_entrenamiento.reshape((x_entrenamiento.shape[0], x_entrenamiento.shape[1],1))
    x_val = x_val.reshape((x_val.shape[0], x_val.shape[1], 1))
    print(x_entrenamiento.shape, y_entrenamiento.shape, x_val.shape, y_val.shape)
    return x_entrenamiento,y_entrenamiento, x_val, y_val

"""## Violky - Entrenamiento"""

rnn=ViolkyRNN(8,6,1,activacion='tanh', perdida='MSE', metrica='RMSE',optimizador='Adagrad')

valores = df.values
valores = valores.astype('float32')
escalar = MinMaxScaler(feature_range=(-1, 1))
valores=valores.reshape(-1, 1) 
escalado = escalar.fit_transform(valores)
datos=rnn.seriesup(escalado,8,1)
x_entrenamiento,y_entrenamiento, x_val, y_val=rnn.validatest(datos)
epocas=61
hist = rnn.entrenamiento(x_entrenamiento, y_entrenamiento, x_val, y_val, epocas)

resul = rnn.validacion(x_entrenamiento, y_val)
compara = pd.DataFrame(np.array([y_val, [x[0] for x in resul]])).transpose()
compara.columns = ['real', 'prediccion']

inverted = escalar.inverse_transform(compara.values)

compara2 = pd.DataFrame(inverted)
compara2.columns = ['real', 'prediccion']

compara2 = pd.DataFrame(inverted)
compara2.columns = ['real', 'prediccion']

compara2['real'].plot(color="#031634",label="Valor Real WTI")
compara2['prediccion'].plot(color="#03565E",label="Predicción WTI")
plt.title('Precio del Petróleo crudo West Texas Intermediate')
plt.xlabel('Día')
plt.ylabel('WTI ($/bbl)')
plt.legend()
plt.xlim(0,len(resul))

plt.show()

n=len(resul)
RMSE=np.zeros(n)
RMSEsum=0

for i in range(0,len(resul)):
  RMSE[i] = np.sqrt((compara2['real'][i] - compara2['prediccion'][i])**2)
  RMSEsum = np.sum(RMSE)/n
plt.plot(range(len(resul)),RMSE, color="#031634")
plt.title('Raíz del Error Cuadrático Medio para los datos sin normalizar')
plt.xlabel('Mes')
plt.ylabel('RMSE')
plt.xlim(0,len(resul))
plt.show()

print('El RMSE es de %0.3f' % RMSEsum)

RMSEData=pd.DataFrame(RMSE)
History=pd.DataFrame(hist)

fig, host = plt.subplots() 
    
par1 = host.twinx()
host.set_xlim(0, epocas-1)
    
host.set_xlabel("Epoca")
host.set_ylabel('Pérdida Conjunto de Entrenamiento')
par1.set_ylabel('Pérdida Conjunto de Validación')

p1, = host.plot(hist['Perdida Entrenamiento'], color="#031634",label="Función de Pérdida C.Entrenamiento")
p2, = par1.plot(hist['Perdida Validación'], color="#03565E" ,label="Función de Pérdida C.Validación")

lns = [p1, p2]
host.legend(handles=lns, loc='best')

plt.title('Función de Pérdida entre los conjuntos de Entrenamiento y Validación')
fig.tight_layout()


fig, host = plt.subplots() 
    
par1 = host.twinx()
host.set_xlim(0, epocas-1)

host.set_xlabel("Epoca")
host.set_ylabel('RMSE Conjunto de Entrenamiento')
par1.set_ylabel('RMSE Conjunto de Validación')

p1, = host.plot(hist['Metrica Entrenamiento'], color="#031634", label="RMSE C.Entrenamiento")
p2, = par1.plot(hist['Metrica Validación'], color="#03565E", label="RMSE C.Validación")

lns = [p1, p2]
host.legend(handles=lns, loc='best')
plt.title('Raíz del Error Cuadrático Medio entre los conjuntos de Entrenamiento y Validación')
fig.tight_layout()

"""## Violky sin Bias- Pronóstico"""

vali = pd.read_csv('/content/drive/MyDrive/Tesis/Base de datos/Datos Validacion.csv')
vali.drop(vali[vali['DCOILWTICO'] == '.'].index, inplace = True)
vali.dropna(inplace=True)
vali['DATE']=pd.to_datetime(vali['DATE'], format='%Y-%m-%d')
vali = vali.set_index('DATE')
vali['DCOILWTICO']=vali['DCOILWTICO'].astype(float)

ultimosMeses = df['2022-01-01':'2022-07-01']
valores = ultimosMeses.values
valores = valores.astype('float32')

valores=valores.reshape(-1, 1) 
scaled = escalar.fit_transform(valores)
reframed = rnn.seriesup(scaled, 8, 1)
reframed.drop(reframed.columns[[6]], axis=1, inplace=True)
reframed.head(6)

valores = reframed.values
x_test = valores[5:, :]
x_test = x_test.reshape((x_test.shape[0], x_test.shape[1],1))

def agregarNuevoValor(x_test,nuevoValor):
  for i in range(x_test.shape[2]-1):
    x_test[0][0][i] = x_test[0][0][i+1]
    x_test[0][0][x_test.shape[2]-1]=nuevoValor
  return x_test

resul=[]
for i in range(31):
  parcial=rnn.val(x_test)
  resul.append(parcial[i])
  x_test=agregarNuevoValor(x_test,parcial[0])

adimen = [x for x in resul]    
adimen1=np.reshape(adimen, (31,1))
inverted = escalar.inverse_transform(adimen1)

prediccionAgosto = pd.DataFrame(inverted)
prediccionAgosto.columns = ['pronostico']
print(prediccionAgosto['pronostico'])
prediccionAgosto.plot()
prediccionAgosto.to_csv('pronostico-RNN-WTI-Violky-Adam.csv')