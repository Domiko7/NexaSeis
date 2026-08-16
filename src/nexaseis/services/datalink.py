import asyncio
import simpledali
import simplemseed
import logging
from datetime import datetime, timezone

from nexaseis.common import get_config, datalink_queue

SAMPLE_RATE = 100

async def _process_incoming_packet(dali, packet: dict) -> None:
    net = packet["station"]["network"]
    code = packet["station"]["code"]
    loc = packet["station"]["location"]
    chan = packet["station"]["channel"]
    
    packet_time = datetime.fromtimestamp(packet["timestamp"], tz=timezone.utc)
    waveform = packet["waveform"]
    num_samples = len(waveform)

    if not num_samples:
        return

    msh = simplemseed.MiniseedHeader(
        net, code, loc, chan, packet_time, num_samples, SAMPLE_RATE
    )

    try:
        encoded_bytes = await asyncio.to_thread(
            simplemseed.encodeSteim1, waveform, 7
        )

        encoded_waveform = simplemseed.EncodedDataSegment(
            simplemseed.seedcodec.STEIM1,
            encoded_bytes,
            num_samples,
            False
        )

        msr = simplemseed.MiniseedRecord(msh, data=encoded_waveform)
        await dali.writeMSeed(msr, 1001)
    except (simpledali.dalipacket.DaliClosed, ConnectionError, OSError):
        raise
    except Exception as e:
        logging.error(f"Error packing/sending mseed chunk for ({net}, {code}, {loc}, {chan}): {e}")


async def datalink_worker():
    config = get_config()
    address, port = config["datalink_server"]["address"].split(":")
    port = int(port)

    while True:
        try:
            logging.info(f"Connecting to DataLink server at {address}:{port}...")
            
            async with simpledali.SocketDataLink(address, port, verbose=False) as dl:
                await dl.id(
                    config["datalink_server"]["program_name"], 
                    config["datalink_server"]["username"], 
                    config["datalink_server"]["process_id"], 
                    config["datalink_server"]["architecture"]
                )
                logging.info("DataLink connection established and handshake completed.")

                while True:
                    packet = await datalink_queue.get()
                    net = packet.get("station", {}).get("network", "UNKNOWN")
                    code = packet.get("station", {}).get("code", "UNKNOWN")
                    
                    try:
                        await _process_incoming_packet(dl, packet)
                    except (simpledali.dalipacket.DaliClosed, ConnectionError, OSError) as e:
                        logging.error(f"DataLink server disconnected while sending packet ({net}, {code}): {e}")
                        raise e
                    except Exception as e:
                        logging.error(f"Failed to encode or send packet: {e}", exc_info=True)
                    finally:
                        datalink_queue.task_done()

        except (ConnectionRefusedError, ConnectionError, OSError, asyncio.TimeoutError, simpledali.dalipacket.DaliClosed) as e:
            logging.warning(f"DataLink server disconnected or errored ({type(e).__name__}: {e}). Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected internal worker crash ({type(e).__name__}: {e}). Restarting in 5 seconds...")
            await asyncio.sleep(5)