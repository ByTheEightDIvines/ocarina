// Ocarina Horse Call: when Link blows the horse call (the Ilia charm, or a horse-grass reed),
// play our ocarina tune instead of the stock reed melody.
//
// How it works:
//  * overlay/Audiores/Stream/horse_ocarina.ast is a new stream file (mono, 44.1 kHz ADPCM)
//    that the mod adds to the game's disc file system.
//  * At startup we register it as a new stream in the sound table (audio_res service).
//  * Both reed calls go through Z2CreatureLink::startLinkVoice with Z2SE_PLAY_REED_UMAKUSA
//    (0x20023). A pre-hook catches that ID, starts our stream and skips the original melody.
//
// Z2Sound.baa is never touched, so this stays compatible with other sound mods.

#include "mods/service.hpp"
#include "mods/svc/audio_res.h"
#include "mods/svc/hook.hpp"
#include "mods/svc/log.h"

#include <cstdint>

#include "JSystem/JAudio2/JAISound.h"
#include "Z2AudioLib/Z2LinkMgr.h"
#include "Z2AudioLib/Z2AudioMgr.h"

DEFINE_MOD();
IMPORT_SERVICE(LogService, svc_log);
IMPORT_SERVICE(HookService, svc_hook);
IMPORT_SERVICE(AudioResService, svc_audio_res);

namespace {

constexpr uint32_t kHorseReedSoundId = 0x20023;  // Z2SE_PLAY_REED_UMAKUSA
constexpr uint32_t kStreamSection = 0x02000000;   // JAISoundID section 2 = streams
constexpr char kStreamPath[] = "/Audiores/Stream/horse_ocarina.ast";

uint16_t g_streamId = 0xFFFF;
AudioSoundTableHandle g_streamHandle = 0;
JAISoundHandle* g_playing = nullptr;

void stop_tune() {
    if (g_playing != nullptr && *g_playing) {
        (*g_playing)->stop();
        g_playing->releaseSound();
    }
}

// Hooked by name: MSVC can't constant-initialize a hook record holding a pointer to a member of
// Z2CreatureLink (it has two base classes). Signature is written receiver-first.
DEFINE_HOOK_SYMBOL("Z2CreatureLink::startLinkVoice",
    Z2SoundHandlePool*(Z2CreatureLink*, JAISoundID, s8), LinkVoice);

HookAction on_link_voice_pre(ModContext*, void* args, void* retval, void*) {
    if (g_streamId == 0xFFFF || g_playing == nullptr) {
        return HOOK_CONTINUE;
    }
    const JAISoundID id = mods::arg<JAISoundID>(args, 1);
    if (static_cast<uint32_t>(id) != kHorseReedSoundId) {
        return HOOK_CONTINUE;
    }

    Z2AudioMgr* audio = Z2AudioMgr::getInterface();  // exported pointer (Z2GetSoundMgr's isn't)
    if (audio == nullptr) {
        return HOOK_CONTINUE;
    }

    stop_tune();  // never stack two copies if the call is spammed
    audio->startSound(JAISoundID(kStreamSection | g_streamId), g_playing, nullptr);

    if (retval != nullptr) {
        *static_cast<Z2SoundHandlePool**>(retval) = nullptr;
    }
    return HOOK_SKIP_ORIGINAL;
}

}  // namespace

extern "C" {

MOD_EXPORT ModResult mod_initialize(ModError* error) {
    AudioSoundTableStreamInfo info = *svc_audio_res->default_stream_info;
    info.volume = 1.0f;
    for (auto& pan : info.pan_parameters) {
        pan = STREAM_PAN_CENTER;  // mono file: keep it centred
    }
    info.stop_on_scene_change = true;

    if (svc_audio_res->add_sound_table_stream(
            mod_ctx, kStreamPath, &info, &g_streamHandle, &g_streamId) != MOD_OK)
    {
        return mods::set_error(error, MOD_ERROR, "could not register the ocarina tune stream");
    }

    g_playing = new JAISoundHandle();

    if (mods::hook::add_pre<LinkVoice>(on_link_voice_pre) != MOD_OK) {
        svc_log->warn(mod_ctx, "could not hook Link's voice starter; the stock reed melody will play");
    } else {
        svc_log->info(mod_ctx, "Ocarina Horse Call ready");
    }
    return MOD_OK;
}

MOD_EXPORT ModResult mod_update(ModError*) {
    return MOD_OK;
}

MOD_EXPORT ModResult mod_shutdown(ModError*) {
    stop_tune();
    delete g_playing;
    g_playing = nullptr;
    if (g_streamHandle != 0) {
        svc_audio_res->remove_sound_table(mod_ctx, g_streamHandle);
        g_streamHandle = 0;
    }
    g_streamId = 0xFFFF;
    return MOD_OK;
}
}
