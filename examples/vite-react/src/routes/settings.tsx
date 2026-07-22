// STK-VITE-04: react-hook-form + zodResolver — one schema drives validation and the
// submit payload type. Saving is a mutation that invalidates what it stales
// (STK-VITE-02); submission renders its three states (STK-VITE-05).
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { saveProfile } from "../api";

const ProfileSchema = z.object({
  displayName: z.string().trim().min(1, "Display name is required").max(60),
  email: z.string().email("Enter a valid email"),
});
type ProfileForm = z.infer<typeof ProfileSchema>;

export default function Settings() {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileForm>({ resolver: zodResolver(ProfileSchema) });

  const mutation = useMutation({
    mutationFn: saveProfile,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <section>
      <h2>Settings</h2>
      <form onSubmit={handleSubmit((values) => mutation.mutate(values))}>
        <div>
          <label htmlFor="displayName">Display name</label>{" "}
          <input id="displayName" {...register("displayName")} />
          {errors.displayName ? (
            <p role="alert">{errors.displayName.message}</p>
          ) : null}
        </div>
        <div>
          <label htmlFor="email">Email</label>{" "}
          <input id="email" type="email" {...register("email")} />
          {errors.email ? <p role="alert">{errors.email.message}</p> : null}
        </div>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </button>
        {mutation.isError ? <p role="alert">Save failed. Try again.</p> : null}
        {mutation.isSuccess ? <p role="status">Saved.</p> : null}
      </form>
    </section>
  );
}
