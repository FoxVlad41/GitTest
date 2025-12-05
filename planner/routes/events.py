from beanie import PydanticObjectId
from fastapi import APIRouter, Body, HTTPException, status
from database.connection import Database
from models.events import Event, EventUpdate
from typing import List

event_database = Database(Event)
event_router = APIRouter(tags=["Events"])

@event_router.get("/", response_model=List[Event])
async def retrieve_all_events() -> List[Event]:
    events = await event_database.get_all()
    return events

@event_router.get("/{id}", response_model=Event)
async def retrieve_event(id: PydanticObjectId) -> Event:
    event = await event_database.get(id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist"
        )
    return event

@event_router.post("/new", response_model=dict)
async def create_event(body: Event = Body(...)) -> dict:
    existing_event = await Event.find_one(Event.title == body.title)
    if existing_event:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Event with this title already exists"
        )
    await event_database.save(body)
    return {"message": "Event created successfully"}

@event_router.put("/{id}", response_model=Event)
async def update_event(id: PydanticObjectId, body: EventUpdate = Body(...)) -> Event:
    updated_event = await event_database.update(id, body)
    if not updated_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist"
        )
    return updated_event

@event_router.delete("/{id}", response_model=dict)
async def delete_event(id: PydanticObjectId) -> dict:
    result = await event_database.delete(id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event with supplied ID does not exist"
        )
    return {"message": "Event deleted successfully"}

@event_router.delete("/", response_model=dict)
async def delete_all_events() -> dict:
    all_events = await event_database.get_all()
    for event in all_events:
        await event.delete()
    return {"message": "All events deleted successfully"}