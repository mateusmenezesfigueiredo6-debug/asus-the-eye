# Matriz de evidências — uma plataforma, 12 recortes de medição

Data de corte: 2026-08-05.

| Questão | Claim | Classe | Evidência favorável | Evidência contrária | Resultado |
|---|---|---|---|---|---|
| Q007 | 103 de 106 artefatos existem | FACT | C101, T101 | existência não prova qualidade | confirmado |
| Q008 | `public-verifier` é a ausência mais antiga | DERIVED | C101, T102 | não há baseline em 30/07 | confirmado quanto à ausência; regressão UNKNOWN |
| Q009 | 106 áreas estão fora do recorte comercial atual | DERIVED | C102, C103, T103 | a plataforma não precisa comercializar todas | confirmado como cenário, não meta |
| Q009 | +130 linhas para configuração um-a-um | DERIVED | C102, C103, T103 | a plataforma pode continuar única e usar agregadores | confirmado somente se o dono escolher esse cenário |
| Q009 | total de regex/pessoas/fontes faltantes | UNKNOWN | C102, C104 | nomes permitem apenas inferência não validada | não mensurável hoje |
| Q009 | Querido Diário devolveu sinal para 138/145 | FACT | C107, T105 | 7 faltantes, 44 zeros e 6 termos suspeitos; execução não foi repetida | evidência de tentativa, não de adequação |
| Q010 | Palantir deve orientar arquitetura | RECOMMENDATION | C105, C104 | custo de padronização | recomendado em fases |
| Q010 | Kalshi deve orientar produto | RECOMMENDATION | C105, C106 | operação financeira requer autoridade | recomendado em modo local/somente-leitura |
| Q011 | 39.087 é o ótimo global da formulação salva | FACT | C107–C110, T107 | o JSON de referência o chamava apenas de limite inferior | confirmado por DP exata entre grupos |
| Q011 | a instância justifica QPU | RECOMMENDATION | C108–C110, T107 | dimensão bruta de 138 variáveis | não: estrutura separável e capacidade 13 permitem solução exata barata |
| Q011 | a solução orienta alocação comercial | UNKNOWN | C107–C110, T107 | 77,8% da base selecionada vem de quatro termos suspeitos; peso e sinergia não medidos | revisão de dados e formulação necessária |
