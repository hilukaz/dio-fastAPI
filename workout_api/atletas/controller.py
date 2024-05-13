import traceback
from datetime import datetime
from typing import List
from uuid import uuid4
from pydantic import UUID4
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, status, Body, HTTPException, Depends
from fastapi_pagination import Page, Params, paginate
from sqlalchemy.future import select
from workout_api.contrib.dependencies import DatabaseDependency
from workout_api.atletas.schemas import AtletaIn, AtletaOut, AtletaUpdate, AtletaSummaryOut
from workout_api.atletas.models import AtletaModel
from workout_api.categorias.models import CategoriaModel
from workout_api.centro_treinamento.models import CentroTreinamentoModel

router = APIRouter()

@router.post(
  '/',
  summary='Criar um novo atleta',
  status_code=status.HTTP_201_CREATED,
  response_model=AtletaOut,
)
async def post(db_session: DatabaseDependency, atleta_in: AtletaIn = Body(...)):
  categoria_nome = atleta_in.categoria.nome
  centro_treinamento_nome = atleta_in.centro_treinamento.nome
  categoria = (await db_session.execute(select(CategoriaModel).filter_by(nome=categoria_nome))).scalars().first()
  
  if not categoria:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'A categoria {categoria_nome} não foi encontrada.')

  centro_treinamento = (await db_session.execute(select(CentroTreinamentoModel).filter_by(nome=centro_treinamento_nome))).scalars().first()
  if not centro_treinamento:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f'O centro de treinamento {centro_treinamento_nome} não foi encontrado.')

  try:
    atleta_out = AtletaOut(id=uuid4(), created_at=datetime.utcnow(), **atleta_in.model_dump())
    atleta_model = AtletaModel(**atleta_out.model_dump(exclude={'categoria', 'centro_treinamento'} ))
    
    atleta_model.categoria_id = categoria.pk_id
    atleta_model.centro_treinamento_id = centro_treinamento.pk_id

    db_session.add(atleta_model)
    await db_session.commit()
  except IntegrityError as exec:
    error_message = str(exec)  # Mensagem de erro da exceção
    # Verifica se o erro está relacionado a violação de integridade do CPF
    if "cpf" in error_message.lower():
      raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, detail=f'Já existe um atleta cadastrado com o CPF: {atleta_in.cpf}')
    else:
      # Caso não seja um erro de violação de CPF, levanta a exceção original
      raise
  except Exception as exec:
    exception_traceback = traceback.format_exc()  # Obtém a pilha de chamadas
    error_message = str(exec)  # Mensagem de erro da exceção
    # Constrói uma mensagem de detalhes mais completa
    detail_message = f'Ocorreu o erro: {error_message}\nTraceback: {exception_traceback}'
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail_message)

  return atleta_out

def get_pagination_params(limit: int = 3, offset: int = 0) -> Params:
  return Params(limit=limit, offset=offset)

@router.get(
  '/',
  summary='Consultar todos os atletas',
  status_code=status.HTTP_200_OK,
  response_model=Page[AtletaSummaryOut],
)
async def query(db_session: DatabaseDependency, params: Params = Depends(get_pagination_params)) -> Page[AtletaSummaryOut]:
  atletas: List[AtletaSummaryOut] = (await db_session.execute(select(AtletaModel))).scalars().all()
  return paginate([AtletaSummaryOut(
    nome=atleta.nome,
    categoria=atleta.categoria.nome,
    centro_treinamento=atleta.centro_treinamento.nome
  ) for atleta in atletas], params=params)

@router.get(
  '/(id)',
  summary='Consultar um atleta pelo id',
  status_code=status.HTTP_200_OK,
  response_model=AtletaOut,
)
async def query(id: UUID4, db_session: DatabaseDependency) -> AtletaOut:
  atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()
  
  if not atleta:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Atleta não encontrado(a) no id:{id}')

  return atleta

@router.get(
  '/(nome)',
  summary='Consultar um atleta pelo nome',
  status_code=status.HTTP_200_OK,
  response_model=AtletaOut,
)
async def query(nome: str, db_session: DatabaseDependency) -> AtletaOut:
  atleta_nome: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(nome=nome))).scalars().first()
  
  if not atleta_nome:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Atleta não encontrado(a) como o nome:{nome}')

  return atleta_nome

@router.get(
  '/(cpf)',
  summary='Consultar um atleta pelo cpf',
  status_code=status.HTTP_200_OK,
  response_model=AtletaOut,
)
async def query(cpf: str, db_session: DatabaseDependency) -> AtletaOut:
  atleta_cpf: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(cpf=cpf))).scalars().first()
  
  if not atleta_cpf:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Atleta não encontrado(a) como o cpf:{cpf}')

  return atleta_cpf

@router.patch(
  '/(id)',
  summary='Editar um atleta pelo id',
  status_code=status.HTTP_200_OK,
  response_model=AtletaOut,
)
async def query(id: UUID4, db_session: DatabaseDependency, atleta_up: AtletaUpdate = Body(...)) -> AtletaOut:
  atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()
  
  if not atleta:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Atleta não encontrado(a) no id:{id}')

  atleta_update = atleta_up.model_dump(exclude_unset=True)
  for key, value in atleta_update.items():
    setattr(atleta, key, value)

  await db_session.commit()
  await db_session.refresh(atleta)
  return atleta

@router.delete(
  '/(id)',
  summary='Deletar um atleta pelo id',
  status_code=status.HTTP_204_NO_CONTENT,
)
async def query(id: UUID4, db_session: DatabaseDependency) -> None:
  atleta: AtletaOut = (await db_session.execute(select(AtletaModel).filter_by(id=id))).scalars().first()
  
  if not atleta:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Atleta não encontrado(a) no id:{id}')

  await db_session.delete(atleta)
  await db_session.commit()
