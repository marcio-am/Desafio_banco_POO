import textwrap
from abc import ABC, abstractclassmethod, abstractproperty
from datetime import datetime
from pathlib import Path

ROOT_PATH = Path(__file__).parent


class ContasIterador:
    def __init__(self, contas):
        self.contas = contas
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        try:
            conta = self.contas[self._index]
            return f"""\
            Agência:\t{conta.agencia}
            Número:\t\t{conta.numero}
            Titular:\t{conta.cliente.nome}
            Saldo:\t\tR$ {conta.saldo:.2f}
        """
        except IndexError:
            raise StopIteration
        finally:
            self._index += 1


class Cliente:
    def __init__(self, endereco):
        self.endereco = endereco
        self.contas = []
        self.indice_conta = 0

    def realizar_transacao(self, conta, transacao):
        if len(conta.historico.transacoes_do_dia()) >= 2:
            print("\n@@@ Você excedeu o número de transações permitidas para hoje! @@@")
            return

        transacao.registrar(conta)

    def adicionar_conta(self, conta):
        self.contas.append(conta)


class PessoaFisica(Cliente):
    def __init__(self, nome, data_nascimento, cpf, endereco):
        super().__init__(endereco)
        self.nome = nome
        self.data_nascimento = data_nascimento
        self.cpf = cpf

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: ('{self.nome}', '{self.cpf}')>"


class Conta:
    def __init__(self, numero, cliente):
        self._saldo = 0
        self._numero = numero
        self._agencia = "0001"
        self._cliente = cliente
        self._historico = Historico()

    @classmethod
    def nova_conta(cls, cliente, numero):
        return cls(numero, cliente)

    @property
    def saldo(self):
        return self._saldo

    @property
    def numero(self):
        return self._numero

    @property
    def agencia(self):
        return self._agencia

    @property
    def cliente(self):
        return self._cliente

    @property
    def historico(self):
        return self._historico

    def sacar(self, valor):
        saldo = self.saldo
        excedeu_saldo = valor > saldo

        if excedeu_saldo:
            print("\n@@@ Operação falhou! Você não tem saldo suficiente. @@@")

        elif valor > 0:
            self._saldo -= valor
            print("\n=== Saque realizado com sucesso! ===")
            return True

        else:
            print("\n@@@ Operação falhou! O valor informado é inválido. @@@")

        return False

    def depositar(self, valor):
        if valor > 0:
            self._saldo += valor
            print("\n=== Depósito realizado com sucesso! ===")
        else:
            print("\n@@@ Operação falhou! O valor informado é inválido. @@@")
            return False

        return True


class ContaCorrente(Conta):
    def __init__(self, numero, cliente, limite=500, limite_saques=3):
        super().__init__(numero, cliente)
        self._limite = limite
        self._limite_saques = limite_saques

    @classmethod
    def nova_conta(cls, cliente, numero, limite, limite_saques):
        return cls(numero, cliente, limite, limite_saques)

    def sacar(self, valor):
        numero_saques = len(
            [transacao for transacao in self.historico.transacoes if transacao["tipo"] == Saque.__name__]
        )

        excedeu_limite = valor > self._limite
        excedeu_saques = numero_saques >= self._limite_saques

        if excedeu_limite:
            print("\n@@@ Operação falhou! O valor do saque excede o limite. @@@")

        elif excedeu_saques:
            print("\n@@@ Operação falhou! Número máximo de saques excedido. @@@")

        else:
            return super().sacar(valor)

        return False

    def __repr__(self):
        return f"<{self.__class__.__name__}: ('{self.agencia}', '{self.numero}', '{self.cliente.nome}')>"

    def __str__(self):
        return f"""\
            Agência:\t{self.agencia}
            C/C:\t\t{self.numero}
            Titular:\t{self.cliente.nome}
        """


class Historico:
    def __init__(self):
        self._transacoes = []

    @property
    def transacoes(self):
        return self._transacoes

    def adicionar_transacao(self, transacao):
        self._transacoes.append(
            {
                "tipo": transacao.__class__.__name__,
                "valor": transacao.valor,
                "data": datetime.utcnow().strftime("%d-%m-%Y %H:%M:%S"),
            }
        )

    def gerar_relatorio(self, tipo_transacao=None):
        for transacao in self._transacoes:
            if tipo_transacao is None or transacao["tipo"].lower() == tipo_transacao.lower():
                yield transacao

    def transacoes_do_dia(self):
        data_atual = datetime.utcnow().date()
        transacoes = []
        for transacao in self._transacoes:
            data_transacao = datetime.strptime(transacao["data"], "%d-%m-%Y %H:%M:%S").date()
            if data_atual == data_transacao:
                transacoes.append(transacao)
        return transacoes


class Transacao(ABC):
    @property
    @abstractproperty
    def valor(self):
        pass

    @abstractclassmethod
    def registrar(self, conta):
        pass


class Saque(Transacao):
    def __init__(self, valor):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso_transacao = conta.sacar(self.valor)

        if sucesso_transacao:
            conta.historico.adicionar_transacao(self)


class Deposito(Transacao):
    def __init__(self, valor):
        self._valor = valor

    @property
    def valor(self):
        return self._valor

    def registrar(self, conta):
        sucesso_transacao = conta.depositar(self.valor)

        if sucesso_transacao:
            conta.historico.adicionar_transacao(self)


def log_transacao(func):
    def envelope(*args, **kwargs):
        resultado = func(*args, **kwargs)
        data_hora = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with open(ROOT_PATH / "log.txt", "a") as arquivo:
            arquivo.write(
                f"[{data_hora}] Função '{func.__name__}' executada com argumentos {args} e {kwargs}. "
                f"Retornou {resultado}\n"
            )
        return resultado

    return envelope



verificacao_cliente = """
[s] Já sou cliente
[n] Não sou cliente. Quero abrir uma conta.
[q] Sair
->"""
menu = """

[d] Depositar  [s] Sacar   [e] Extrato
[c] Quero abrir outra conta.     [q] Sair

=> """

saldo = 0
limite = 500
extrato = ""
clientes = list()
contas = list()
numero_saques = 0
LIMITE_SAQUES = 3
conts = 1

# Definindo as funções 
def depositarFN(valor):
    saldo_deposito = saldo
    saldo_deposito += valor
    return saldo_deposito    

def sacarFN(valor_fn = "valor"):
    saldo_sacar = saldo
    saldo_sacar -= valor_fn
    return saldo_sacar

def extratoFN(valor, tipo = ""):
    if tipo == "sacar":
        extrato_func = extrato
        extrato_func += f"Saque: R$ {valor:.2f}\n" 
    elif tipo == "depositar":
        extrato_func = extrato
        extrato_func += f"Depósito: R$ {valor:.2f}\n"

    return extrato_func

def cadastroFN(cpf,nascimento,endereco):
    clientes_fn = clientes
    clientes_fn.append([cpf,nascimento,endereco])
    return clientes_fn

def contadorFN(const_fn):
     const_fn += 1
     return const_fn
     
def contasFN(conts):
     cpf_fn = input(str("Digite seu CPF sem pontos e traço (Somente números):"))
     conta_fn = contas
     conta_fn += [cpf_fn, "0001", f"{conts}"]
     conts = contadorFN(conts)
     return conta_fn, cpf_fn, conts

     
while True:
    entrada = input(verificacao_cliente)
    
    

    if entrada == "n":
                # cpf = input(str("Digite seu CPF sem pontos e traço (Somente números):"))
                contas, cpf, conts = contasFN(conts)
                nascimento = input("Digite a sua data de nascimento:")
                endereco = input(str("Digite seu endereço:"))
                clientes.append([cadastroFN(cpf,nascimento,endereco)], )
                print(f"Sua conta foi criada.")
                print(contas)
    
    if entrada == "s":
        opcao = input(menu)
        if opcao == "d":

            valor = float(input("Informe o valor do depósito: "))
                

            if valor>0:

                saldo = depositarFN(valor)
                extrato = extratoFN(valor,tipo="depositar")
                    
                print("Depósito realizado com sucesso.")

            else:
                print("Operação falhou! O valor informado é inválido.")

        elif opcao == "s":
                
            if (numero_saques < LIMITE_SAQUES) and (valor <= limite) and (valor <= saldo):
                valor = float(input("Informe o valor do saque: "))

                saldo = sacarFN(valor_fn=valor)
                extrato = extratoFN(valor,tipo="sacar")

                print("Saque efetuado com sucesso!")
                numero_saques += 1
                    
                    
            elif numero_saques >= LIMITE_SAQUES:

                print("Operação falhou! Número máximo de saques diários excedido!")
            elif valor >= saldo:
                print("Operação falhou! Seu saldo é insuficiente!")

            elif valor >= limite:
                print("Operação falhou! O valor excede o limite máximo permitido!")

            else:
                print("Operação falhou! O valor informado é inválido.")
                
                

        elif opcao == "e":
            print("\n================ EXTRATO ================")
            print("Não foram realizadas movimentações." if not extrato else extrato)
            print(f"\nSaldo: R$ {saldo:.2f}")
            print("==========================================")

        elif opcao == "c":
                contas, cpf, conts = contasFN(conts)
                print(f"Sua conta foi criada.")
                print(contas)
        
        elif opcao == "q":
             break
             
    elif entrada == "q":
        break
print(clientes)
        # else:
        #     print("Operação inválida, por favor selecione novamente a operação desejada.")
                


