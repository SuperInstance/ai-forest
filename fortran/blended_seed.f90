! Blended Seed — FM's fact preservation + O1's novelty, mixed by α
!
! α = 0.0 → pure FM: constraint encoding, facts preserved
! α = 0.5 → balanced: facts anchor, novelty explores
! α = 1.0 → pure O1: maximum divergence, creative variation
!
! This IS the ADJOIN opcode (0xFC) — composing two adjunctions.

module blended_seed
  use, intrinsic :: iso_c_binding
  implicit none

  ! FM's parameters (constraint encoding strength)
  integer(c_int32_t), parameter :: FM_CLAMP_MIN = 0
  integer(c_int32_t), parameter :: FM_CLAMP_MAX = 16777215  ! 24-bit max

  ! O1's parameters (perturbation magnitude)
  integer(c_int32_t), parameter :: O1_DEFAULT_MAG = 5000

contains

  ! ── ADJOIN: blend FM's fact preservation with O1's novelty
  !
  ! tiles_in:  input array of tile values
  ! n:         number of tiles
  ! alpha:     blend factor (0-1024, where 1024=1.0)
  !            0 = pure FM (facts preserved, no mutation)
  !            512 = balanced (facts anchor, moderate mutation)
  !            1024 = pure O1 (max variation, facts may drift)
  ! seed:      RNG seed
  ! tiles_out: output array
  ! n_out:     number of output tiles
  !
  ! The adjunction composition:
  !   θ_total = α × θ_O1 + (1024-α) × θ_FM
  !   θ_FM = constraint clamping (preserves values within bounds)
  !   θ_O1 = perturbation (adds noise for novelty)

  subroutine adjoin(tiles_in, n, alpha, seed, tiles_out, n_out) &
       bind(c, name="adjoin")
    integer(c_int32_t), intent(in)  :: tiles_in(n)
    integer(c_int32_t), intent(in), value :: n, alpha, seed
    integer(c_int32_t), intent(out) :: tiles_out(n)
    integer(c_int32_t), intent(out) :: n_out

    integer(c_int32_t) :: i, perturbed, clamped
    integer(c_int32_t) :: fm_weight, o1_weight
    integer(c_int64_t) :: rng

    n_out = min(n, 256)
    rng = int(seed, c_int64_t)
    
    ! FM weight = how much to clamp (high = preserve facts)
    ! O1 weight = how much to perturb (high = generate novelty)
    fm_weight = 1024 - alpha
    o1_weight = alpha

    do i = 1, n_out
       ! Step 1: O1 perturbation (always applied, scaled by alpha)
       rng = mod(rng * 6364136223846793005_c_int64_t + 1442695040888963407_c_int64_t, 9223372036854775807_c_int64_t)
       if (o1_weight > 0) then
          perturbed = tiles_in(i) + int(mod(rng, int(o1_weight, c_int64_t)), c_int32_t)
       else
          perturbed = tiles_in(i)
       end if

       ! Step 2: FM clamping (always applied, scaled by (1024-alpha))
       ! Stronger clamping = less deviation from original
       clamped = perturbed - (perturbed - tiles_in(i)) * (1024 - alpha) / 1024

       ! Step 3: FM constraint bounds
       if (clamped < FM_CLAMP_MIN) clamped = FM_CLAMP_MIN
       if (clamped > FM_CLAMP_MAX) clamped = FM_CLAMP_MAX

       tiles_out(i) = clamped
    end do

    ! Alpha determines how many tiles survive
    ! Low alpha = FM preserves almost everything
    ! High alpha = O1 filters aggressively
    n_out = min(n_out * (512 + alpha) / 1024, n)
    if (n_out < 1) n_out = 1
  end subroutine adjoin

end module blended_seed
