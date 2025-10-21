import { useState } from "react";
import { Button, Container, Title, Text, Paper, Stack, Center, TextInput, Divider } from "@mantine/core";
import { IconBrandDiscord, IconPhone } from "@tabler/icons-react";
import { notifications } from "@mantine/notifications";
import * as auth from "../api/auth";
import { useUserStore } from "../hooks/useUserStore";

export default function ConnectDiscord() {
  const [isConnecting, setIsConnecting] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState("");
  const [isSubmittingPhone, setIsSubmittingPhone] = useState(false);

  const [name, email, role, location, zoomlink, discord, getUser] = useUserStore((store) => [
    store.name,
    store.email,
    store.role,
    store.location,
    store.zoomlink,
    store.discord,
    store.getUser,
  ]);

  const handleConnectDiscord = () => {
    setIsConnecting(true);
    // Redirect to Discord OAuth login
    window.location.href = "/api/auth/discord/login";
  };

  const formatPhoneNumber = (value: string) => {
    // Remove all non-digits
    const phoneDigits = value.replace(/\D/g, '');

    // Limit to 10 digits
    const limitedDigits = phoneDigits.slice(0, 10);

    // Format as (XXX) XXX-XXXX
    if (limitedDigits.length <= 3) {
      return limitedDigits;
    } else if (limitedDigits.length <= 6) {
      return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3)}`;
    } else {
      return `(${limitedDigits.slice(0, 3)}) ${limitedDigits.slice(3, 6)}-${limitedDigits.slice(6)}`;
    }
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const formatted = formatPhoneNumber(e.target.value);
    setPhoneNumber(formatted);
  };

  const handleSubmitPhone = async () => {
    // Validate phone number has exactly 10 digits
    const digits = phoneNumber.replace(/\D/g, '');
    if (digits.length !== 10) {
      notifications.show({
        title: "Invalid Phone Number",
        color: "red",
        message: "Please enter a valid 10-digit US phone number",
      });
      return;
    }

    setIsSubmittingPhone(true);
    try {
      const res = await auth.updateUser({
        name: name,
        email: email,
        role: role,
        location: location,
        zoomlink: zoomlink,
        password: "",
        discord: discord,
        phone: phoneNumber,
        preferred: "Phone"
      });

      if (res.ok) {
        notifications.show({
          title: "Success!",
          color: "green",
          message: "Phone number saved as preferred contact method",
        });
        getUser();
      } else {
        notifications.show({
          title: "Error",
          color: "red",
          message: res.message,
        });
      }
    } catch (error) {
      notifications.show({
        title: "Error",
        message: "Failed to save phone number",
        color: "red",
      });
    } finally {
      setIsSubmittingPhone(false);
    }
  };

  return (
    <Container size="sm" py="6rem">
      <Paper p="xl" shadow="xs" className="bg-neutral-800">
        <Stack gap="xl" align="center">
          <IconBrandDiscord size={64} color="#5865F2" />

          <Title order={2} ta="center">
            Connect Your Contact Information
          </Title>

          <Text ta="center" c="dimmed">
            To use QStack, you need to provide contact information.
            This allows mentors and organizers to reach you for help.
          </Text>

          <Center w="100%">
            <Button
              leftSection={<IconBrandDiscord size={20} />}
              size="lg"
              color="indigo"
              onClick={handleConnectDiscord}
              loading={isConnecting}
              disabled={isConnecting}
              fullWidth
            >
              Connect Discord
            </Button>
          </Center>

          <Text ta="center" size="xs" c="dimmed">
            You'll be redirected to Discord to authorize QStack
          </Text>

          <Divider label="OR" labelPosition="center" w="100%" />

          <Stack gap="md" w="100%">
            <Text ta="center" c="dimmed" size="sm">
              Prefer not to use Discord? Provide your phone number instead:
            </Text>

            <TextInput
              leftSection={<IconPhone size={20} />}
              placeholder="(123) 456-7890"
              value={phoneNumber}
              onChange={handlePhoneChange}
              maxLength={14}
              size="md"
              onKeyPress={(e) => {
                if (e.key === "Enter") {
                  handleSubmitPhone();
                }
              }}
            />

            <Button
              size="lg"
              color="teal"
              onClick={handleSubmitPhone}
              loading={isSubmittingPhone}
              disabled={isSubmittingPhone || phoneNumber.replace(/\D/g, '').length !== 10}
              fullWidth
            >
              Submit Phone Number
            </Button>
          </Stack>
        </Stack>
      </Paper>
    </Container>
  );
}